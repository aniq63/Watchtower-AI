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
        Creates or updates baseline information for the project.
        Returns True if baseline was created/updated, False otherwise.
        """
        async for db in get_db():
            try:
                # 1. Fetch project data stats
                data_stats_result = await db.execute(
                    select(models.ProjectDataStats).where(
                        models.ProjectDataStats.project_id == self.project_id
                    )
                )
                data_stats = data_stats_result.scalars().first()
                
                if not data_stats:
                    print(f"No data stats found for project {self.project_id}")
                    return False
                
                latest_feature_start_row = data_stats.latest_feature_start_row
                latest_feature_end_row = data_stats.latest_feature_end_row
                latest_prediction_start_row = data_stats.latest_prediction_start_row
                latest_prediction_end_row = data_stats.latest_prediction_end_row
                
                # 2. Fetch project config (settings)
                config_result = await db.execute(
                    select(models.ProjectConfig).where(
                        models.ProjectConfig.project_id == self.project_id
                    )
                )
                project_config = config_result.scalars().first()
                
                if not project_config:
                    print(f"No project config found for project {self.project_id}")
                    return False
                
                baseline_batch_size = project_config.baseline_batch_size
                monitor_batch_size = project_config.monitor_batch_size
                
                # 3. Fetch or create baseline info with locking for atomicity
                baseline_result = await db.execute(
                    select(models.BaselineInfo).where(
                        models.BaselineInfo.project_id == self.project_id
                    )
                )
                baseline_info = baseline_result.scalars().first()
                
                # 4. Determine if we need to create or update baseline
                if not baseline_info:
                    # Create new baseline if we have enough data (either Features or Predictions)
                    has_enough_features = latest_feature_end_row and latest_feature_end_row >= baseline_batch_size
                    has_enough_predictions = latest_prediction_end_row and latest_prediction_end_row >= baseline_batch_size

                    if has_enough_features or has_enough_predictions:
                        
                        feat_start = 1 if has_enough_features else 0
                        feat_end = baseline_batch_size if has_enough_features else 0
                        
                        pred_start = 1 if has_enough_predictions else 0
                        pred_end = baseline_batch_size if has_enough_predictions else 0

                        new_baseline = models.BaselineInfo(
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
                            # Check if another process created it already (race condition)
                            baseline_result = await db.execute(
                                select(models.BaselineInfo).where(
                                    models.BaselineInfo.project_id == self.project_id
                                )
                            )
                            baseline_info = baseline_result.scalars().first()
                            if baseline_info:
                                print(f"⚠ Baseline already created by another process for project {self.project_id}")
                                return True
                            raise
                        
                        print(f"✓ Created baseline for project {self.project_id}")
                        print(f"  Feature range: {feat_start} to {feat_end}")
                        print(f"  Prediction range: {pred_start} to {pred_end}")
                        
                        # Create initial monitor info
                        await self._create_monitor_info(db, baseline_batch_size, monitor_batch_size)
                        
                        return True
                    else:
                        print(f"Not enough data to create baseline (need {baseline_batch_size} rows of features or predictions)")
                        return False
                
                else:
                    # Update existing baseline if needed
                    current_baseline_end_feature = baseline_info.baseline_end_row_feature_input
                    current_baseline_end_prediction = baseline_info.baseline_end_row_prediction_output
                    temp_baseline_size = baseline_info.temp_baseline_batch_size
                    
                    # Check if we have enough new data to extend baseline
                    next_baseline_target = temp_baseline_size + baseline_batch_size
                    
                    has_enough_features = latest_feature_end_row and latest_feature_end_row >= next_baseline_target
                    has_enough_predictions = latest_prediction_end_row and latest_prediction_end_row >= next_baseline_target

                    if has_enough_features or has_enough_predictions:
                        
                        # Update baseline ranges
                        if has_enough_features:
                            baseline_info.baseline_start_row_feature_input = current_baseline_end_feature + 1
                            baseline_info.baseline_end_row_feature_input = next_baseline_target
                        
                        if has_enough_predictions:
                            baseline_info.baseline_start_row_prediction_output = current_baseline_end_prediction + 1
                            baseline_info.baseline_end_row_prediction_output = next_baseline_target
                            
                        baseline_info.temp_baseline_batch_size = next_baseline_target
                        
                        await db.commit()
                        
                        print(f"✓ Updated baseline for project {self.project_id}")
                        print(f"  Feature range: {baseline_info.baseline_start_row_feature_input} to {baseline_info.baseline_end_row_feature_input}")
                        print(f"  Prediction range: {baseline_info.baseline_start_row_prediction_output} to {baseline_info.baseline_end_row_prediction_output}")
                        
                        # Update monitor info
                        await self._update_monitor_info(db, next_baseline_target, monitor_batch_size)
                        
                        return True
                    else:
                        print(f"Not enough new data to update baseline (need {next_baseline_target} rows)")
                        return False
                        
            except Exception as e:
                await db.rollback()
                print(f"Error creating/updating baseline: {str(e)}")
                return False
    
    async def _create_monitor_info(self, db, baseline_end_row: int, monitor_batch_size: int):
        """Create initial monitor info entry after baseline is established."""
        try:
            # Check if monitor info already exists
            monitor_result = await db.execute(
                select(models.MonitorInfo).where(
                    models.MonitorInfo.project_id == self.project_id
                )
            )
            existing_monitor = monitor_result.scalars().first()
            
            if not existing_monitor:
                monitor_start = baseline_end_row + 1
                monitor_end = baseline_end_row + monitor_batch_size
                
                new_monitor = models.MonitorInfo(
                    project_id=self.project_id,
                    monitor_start_row_feature_input=monitor_start,
                    monitor_end_row_feature_input=monitor_end
                )
                
                db.add(new_monitor)
                await db.commit()
                
                print(f"✓ Created monitor info: rows {monitor_start} to {monitor_end}")
        
        except Exception as e:
            print(f"Error creating monitor info: {str(e)}")
    
    async def _update_monitor_info(self, db, baseline_end_row: int, monitor_batch_size: int):
        """Update monitor info entry when baseline is extended."""
        try:
            monitor_result = await db.execute(
                select(models.MonitorInfo).where(
                    models.MonitorInfo.project_id == self.project_id
                )
            )
            monitor_info = monitor_result.scalars().first()
            
            if monitor_info:
                monitor_info.monitor_start_row_feature_input = baseline_end_row + 1
                monitor_info.monitor_end_row_feature_input = baseline_end_row + monitor_batch_size
                
                await db.commit()
                
                print(f"✓ Updated monitor info: rows {monitor_info.monitor_start_row_feature_input} to {monitor_info.monitor_end_row_feature_input}")
        
        except Exception as e:
            print(f"Error updating monitor info: {str(e)}")
    
    async def get_baseline_data(self):
        """
        Retrieves the current baseline data for features and predictions.
        Returns a dictionary with baseline ranges and data.
        """
        async for db in get_db():
            baseline_result = await db.execute(
                select(models.BaselineInfo).where(
                    models.BaselineInfo.project_id == self.project_id
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
            baseline_feature_timestamp = feature_rows[-1].created_at if feature_rows else None
            baseline_prediction_timestamp = prediction_rows[-1].created_at if prediction_rows else None
            
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
                select(models.MonitorInfo).where(
                    models.MonitorInfo.project_id == self.project_id
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
            monitor_feature_timestamp = feature_rows[-1].created_at if feature_rows else None
            
            # Calculate actual range using actual retrieved rows (ensures we don't report more rows than we have)
            actual_start = feature_rows[0].row_id if feature_rows else monitor_info.monitor_start_row_feature_input
            actual_end = feature_rows[-1].row_id if feature_rows else monitor_info.monitor_end_row_feature_input
            
            return {
                'monitor_id': monitor_info.monitor_id,
                'feature_range': (
                    actual_start,
                    actual_end
                ),
                'feature_data': [row.features for row in feature_rows],
                'total_rows': len(feature_rows),
                'monitor_feature_timestamp': monitor_feature_timestamp
            }
