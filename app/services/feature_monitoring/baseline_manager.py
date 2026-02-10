import asyncio
import pandas as pd
from sqlalchemy import select
from app.database import models
from app.database.connection import get_db

class BaselineManager:
    """
    Manages baseline creation and updates for both feature inputs and prediction outputs.
    Also handles monitor info creation for tracking monitoring windows.
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
    
    async def create_baseline(self):
        """
        Creates or updates baseline to use the most recent complete batch.
        Baseline SLIDES FORWARD when 1000 new rows arrive.
        Returns True if baseline exists, False otherwise.
        """
        async for db in get_db():
            try:
                # 1. Get project data stats
                data_stats_result = await db.execute(
                    select(models.FeatureStats).where(
                        models.FeatureStats.project_id == self.project_id
                    )
                )
                data_stats = data_stats_result.scalars().first()
                
                if not data_stats:
                    return False
                
                latest_feature_end_row = data_stats.latest_feature_end_row
                latest_prediction_end_row = data_stats.latest_prediction_end_row
                
                # 2. Get project config
                config_result = await db.execute(
                    select(models.FeatureConfig).where(
                        models.FeatureConfig.project_id == self.project_id
                    )
                )
                project_config = config_result.scalars().first()
                
                if not project_config:
                    # Create default config if not exists
                    print(f"⚠ No config found for project {self.project_id}. Creating default config.")
                    project_config = models.FeatureConfig(
                        project_id=self.project_id,
                        baseline_batch_size=1000,
                        monitor_batch_size=500,
                        monitoring_stage="model_input"
                    )
                    try:
                        db.add(project_config)
                        await db.commit()
                        await db.refresh(project_config)
                    except Exception as e:
                        await db.rollback()
                        # Fetch again in case of race condition
                        config_result = await db.execute(
                            select(models.FeatureConfig).where(
                                models.FeatureConfig.project_id == self.project_id
                            )
                        )
                        project_config = config_result.scalars().first()
                        if not project_config:
                            print(f"❌ Failed to create default config: {e}")
                            return False
                
                baseline_batch_size = project_config.baseline_batch_size
                monitor_batch_size = project_config.monitor_batch_size
                
                # 3. Check if baseline exists
                baseline_result = await db.execute(
                    select(models.FeatureBaseline).where(
                        models.FeatureBaseline.project_id == self.project_id
                    )
                )
                baseline_info = baseline_result.scalars().first()
                
                # 4. Calculate the most recent complete baseline window
                has_enough_features = latest_feature_end_row and latest_feature_end_row >= baseline_batch_size
                has_enough_predictions = latest_prediction_end_row and latest_prediction_end_row >= baseline_batch_size
                
                if not (has_enough_features or has_enough_predictions):
                    return False
                
                # Most recent baseline is the last N rows
                feat_start = latest_feature_end_row - baseline_batch_size + 1 if has_enough_features else 0
                feat_end = latest_feature_end_row if has_enough_features else 0
                
                pred_start = latest_prediction_end_row - baseline_batch_size + 1 if has_enough_predictions else 0
                pred_end = latest_prediction_end_row if has_enough_predictions else 0
                
                if not baseline_info:
                    # Create new baseline
                    new_baseline = models.FeatureBaseline(
                        project_id=self.project_id,
                        baseline_start_row_feature_input=feat_start,
                        baseline_end_row_feature_input=feat_end,
                        baseline_start_row_prediction_output=pred_start,
                        baseline_end_row_prediction_output=pred_end,
                        temp_baseline_batch_size=baseline_batch_size
                    )
                    
                    try:
                        db.add(new_baseline)
                        await db.commit()
                        await db.refresh(new_baseline)
                    except Exception as e:
                        await db.rollback()
                        baseline_result = await db.execute(
                            select(models.FeatureBaseline).where(
                                models.FeatureBaseline.project_id == self.project_id
                            )
                        )
                        baseline_info = baseline_result.scalars().first()
                        if baseline_info:
                            return True
                        raise
                    
                    print(f"\n📊 BASELINE CREATED (Project {self.project_id})")
                    print(f"   └─ Rows: {feat_start} to {feat_end}")
                    
                    # Create initial monitor window
                    await self._create_or_update_monitor(db, feat_end, latest_feature_end_row, monitor_batch_size)
                    
                else:
                    # Check if we should update baseline (slide forward)
                    current_baseline_end = baseline_info.baseline_end_row_feature_input
                    
                    # If we have 1000+ new rows beyond current baseline, slide it forward
                    if latest_feature_end_row >= current_baseline_end + baseline_batch_size:
                        baseline_info.baseline_start_row_feature_input = feat_start
                        baseline_info.baseline_end_row_feature_input = feat_end
                        
                        if has_enough_predictions:
                            baseline_info.baseline_start_row_prediction_output = pred_start
                            baseline_info.baseline_end_row_prediction_output = pred_end
                        
                        await db.commit()
                        
                        print(f"\n📊 BASELINE UPDATED (Project {self.project_id})")
                        print(f"   └─ Rows: {feat_start} to {feat_end} (slid forward)")
                
                return True
                
            except Exception as e:
                await db.rollback()
                return False
    
    async def _create_or_update_monitor(self, db, baseline_end_row: int, latest_row: int, monitor_batch_size: int):
        """
        Creates or updates the monitor window to slide forward.
        Monitor window is the LAST N rows (where N = monitor_batch_size).
        """
        try:
            # Check if monitor info already exists
            monitor_result = await db.execute(
                select(models.FeatureMonitorInfo).where(
                    models.FeatureMonitorInfo.project_id == self.project_id
                )
            )
            monitor_info = monitor_result.scalars().first()
            
            # Calculate sliding monitor window (last N rows)
            if latest_row > baseline_end_row:
                # We have data beyond baseline
                monitor_end = latest_row
                monitor_start = max(baseline_end_row + 1, latest_row - monitor_batch_size + 1)
            else:
                # Not enough data beyond baseline yet
                return
            
            if monitor_info:
                # Update existing monitor window
                monitor_info.monitor_start_row_feature_input = monitor_start
                monitor_info.monitor_end_row_feature_input = monitor_end
                await db.commit()
                print(f"📈 Monitor window: rows {monitor_start} to {monitor_end} ({monitor_end - monitor_start + 1} rows)")
            else:
                # Create new monitor window
                new_monitor = models.FeatureMonitorInfo(
                    project_id=self.project_id,
                    monitor_start_row_feature_input=monitor_start,
                    monitor_end_row_feature_input=monitor_end
                )
                db.add(new_monitor)
                await db.commit()
                print(f"📈 Monitor window: rows {monitor_start} to {monitor_end} ({monitor_end - monitor_start + 1} rows)")
        
        except Exception as e:
            pass
    
    async def update_monitor_window(self):
        """
        Updates the monitor window to slide forward after new data ingestion.
        Should be called after each batch ingestion (after baseline exists).
        """
        async for db in get_db():
            try:
                # 1. Get baseline info
                baseline_result = await db.execute(
                    select(models.FeatureBaseline).where(
                        models.FeatureBaseline.project_id == self.project_id
                    )
                )
                baseline_info = baseline_result.scalars().first()
                
                if not baseline_info:
                    # No baseline exists yet
                    return False
                
                # 2. Get current data stats
                data_stats_result = await db.execute(
                    select(models.FeatureStats).where(
                        models.FeatureStats.project_id == self.project_id
                    )
                )
                data_stats = data_stats_result.scalars().first()
                
                if not data_stats:
                    return False
                
                # 3. Get config
                config_result = await db.execute(
                    select(models.FeatureConfig).where(
                        models.FeatureConfig.project_id == self.project_id
                    )
                )
                project_config = config_result.scalars().first()
                
                if not project_config:
                    # Create default config if not exists
                    print(f"⚠ No config found for project {self.project_id}. Creating default config.")
                    project_config = models.FeatureConfig(
                        project_id=self.project_id,
                        baseline_batch_size=1000,
                        monitor_batch_size=500,
                        monitoring_stage="model_input"
                    )
                    try:
                        db.add(project_config)
                        await db.commit()
                        await db.refresh(project_config)
                    except Exception as e:
                        await db.rollback()
                        return False
                
                # 4. Update monitor window (slide forward)
                baseline_end = baseline_info.baseline_end_row_feature_input
                latest_row = data_stats.latest_feature_end_row
                monitor_batch_size = project_config.monitor_batch_size
                
                await self._create_or_update_monitor(db, baseline_end, latest_row, monitor_batch_size)
                
                return True
                
            except Exception as e:
                return False
    
    
    async def get_baseline_data(self):
        """
        Retrieves the current baseline data for features and predictions.
        Returns a dictionary with baseline ranges and data.
        """
        async for db in get_db():
            baseline_result = await db.execute(
                select(models.FeatureBaseline).where(
                    models.FeatureBaseline.project_id == self.project_id
                )
            )
            baseline_info = baseline_result.scalars().first()
            
            if not baseline_info:
                return None
            
            # Fetch feature baseline data
            feature_result = await db.execute(
                select(models.FeatureInput).where(
                    models.FeatureInput.project_id == self.project_id,
                    models.FeatureInput.row_id.between(
                        baseline_info.baseline_start_row_feature_input,
                        baseline_info.baseline_end_row_feature_input
                    )
                )
            )
            feature_rows = feature_result.scalars().all()
            
            # Fetch prediction baseline data
            prediction_result = await db.execute(
                select(models.PredictionOutput).where(
                    models.PredictionOutput.project_id == self.project_id,
                    models.PredictionOutput.row_id.between(
                        baseline_info.baseline_start_row_prediction_output,
                        baseline_info.baseline_end_row_prediction_output
                    )
                )
            )
            prediction_rows = prediction_result.scalars().all()
            
            # Get timestamps from last rows in each batch for traceability
            # Strip timezone to match TIMESTAMP WITHOUT TIME ZONE columns in drift tables
            baseline_feature_timestamp = feature_rows[-1].created_at.replace(tzinfo=None) if feature_rows else None
            baseline_prediction_timestamp = prediction_rows[-1].created_at.replace(tzinfo=None) if prediction_rows else None
            
            return {
                'baseline_id': baseline_info.baseline_id,
                'feature_range': (
                    baseline_info.baseline_start_row_feature_input,
                    baseline_info.baseline_end_row_feature_input
                ),
                'prediction_range': (
                    baseline_info.baseline_start_row_prediction_output,
                    baseline_info.baseline_end_row_prediction_output
                ),
                'feature_data': [row.features for row in feature_rows],
                'prediction_data': [row.prediction for row in prediction_rows],
                'created_at': baseline_info.created_at,
                'baseline_feature_timestamp': baseline_feature_timestamp,
                'baseline_prediction_timestamp': baseline_prediction_timestamp
            }
    
    async def get_monitor_data(self):
        """
        Retrieves the current monitoring window data for features.
        Returns a dictionary with monitor ranges and data.
        This data is used for drift detection against the baseline.
        """
        async for db in get_db():
            monitor_result = await db.execute(
                select(models.FeatureMonitorInfo).where(
                    models.FeatureMonitorInfo.project_id == self.project_id
                )
            )
            monitor_info = monitor_result.scalars().first()
            
            if not monitor_info:
                return None
            
            # Fetch feature monitoring data
            feature_result = await db.execute(
                select(models.FeatureInput).where(
                    models.FeatureInput.project_id == self.project_id,
                    models.FeatureInput.row_id.between(
                        monitor_info.monitor_start_row_feature_input,
                        monitor_info.monitor_end_row_feature_input
                    )
                )
            )
            feature_rows = feature_result.scalars().all()
            
            # Get timestamp from last row in monitor window for traceability
            # Strip timezone to match TIMESTAMP WITHOUT TIME ZONE columns in drift tables
            monitor_feature_timestamp = feature_rows[-1].created_at.replace(tzinfo=None) if feature_rows else None
            
            # Calculate actual range using actual retrieved rows (ensures we don't report more rows than we have)
            actual_start = feature_rows[0].row_id if feature_rows else monitor_info.monitor_start_row_feature_input
            actual_end = feature_rows[-1].row_id if feature_rows else monitor_info.monitor_end_row_feature_input
            
            return {
                'project_id': self.project_id,
                'feature_range': (
                    actual_start,
                    actual_end
                ),
                'feature_data': [row.features for row in feature_rows],
                'total_rows': len(feature_rows),
                'monitor_feature_timestamp': monitor_feature_timestamp
            }
