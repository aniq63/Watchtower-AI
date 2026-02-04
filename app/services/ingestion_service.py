# app/services/ingestion_service.py
import asyncio
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.database.models import FeatureInput, ProjectDataStats, DataQualityCheck
from app.services.store_data_for_validation import StoreDataValidation
from app.services.data_validation import DataValidation
from app.services.baseline_manager import BaselineManager
from app.services.check_data_quality import DataQualityChecker
from app.services.data_drift import InputDataDriftMonitor
from app.services.model_based_data_drift import ModelBasedDriftMonitor
from app.database.connection import AsyncSessionLocal

class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest(self, project_id: int, features: list, stage: str = "model_input", event_time=None, metadata=None):
        """
        Save features/predictions into DB with sequential row_id and stage
        """
        event_time = event_time or datetime.utcnow()
        rows_ingested = 0

        # Get current max row_id for this project to continue sequence
        result = await self.db.execute(
            select(func.max(FeatureInput.row_id)).where(FeatureInput.project_id == project_id)
        )
        max_row_id = result.scalar() or 0
        current_row_id = max_row_id

        # Save features
        if isinstance(features, dict):
            features = [features]
            
        for row in features:
            current_row_id += 1
            feature_row = FeatureInput(
                project_id=project_id,
                row_id=current_row_id,
                features=row,
                stage=stage,  # Store stage
                created_at=event_time
            )
            self.db.add(feature_row)
            rows_ingested += 1

        

        # -------- Update Project Data Stats ---------
        
        # Calculate ranges for this batch
        # Features range
        feat_start = (max_row_id + 1) if rows_ingested > 0 else None
        feat_end = current_row_id if rows_ingested > 0 else None
        
        
        # Fetch existing stats or create new
        stmt = select(ProjectDataStats).where(ProjectDataStats.project_id == project_id)
        result = await self.db.execute(stmt)
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = ProjectDataStats(
                project_id=project_id,
                total_batches=0,
                last_ingestion_at=event_time
            )
            self.db.add(stats)
        
        # Update stats
        stats.total_batches += 1
        stats.last_ingestion_at = event_time
        
        if feat_start is not None:
            stats.latest_feature_start_row = feat_start
            stats.latest_feature_end_row = feat_end
            


        # ----------------------- Data Validation -----------------
        # 1. Store/Ensure Validation Parameters Exist
        store_val = StoreDataValidation(project_id=project_id)
        await store_val.store_validation_data(features=features)
        
        # 2. Run Validation for this Batch
        validator = DataValidation(features=features, project_id=project_id)
        await validator.check_data_validation(batch_number=stats.total_batches)

        # ----------------------- Baseline Creation -----------------
        # Create or update baseline after validation
        baseline_mgr = BaselineManager(project_id=project_id)
        baseline_created = await baseline_mgr.create_baseline()
        
        # Retrieve baseline data for future drift detection
        baseline_data = await baseline_mgr.get_baseline_data()
        if baseline_data:
            print(f"✓ Baseline data retrieved for project {project_id}")
            print(f"  Feature baseline: {len(baseline_data['feature_data'])} rows")
            print(f"  Prediction baseline: {len(baseline_data['prediction_data'])} rows")
        
        # Retrieve monitor data for drift detection
        monitor_data = await baseline_mgr.get_monitor_data()
        if monitor_data:
            print(f"✓ Monitor data retrieved for project {project_id}")
            print(f"  Monitor window: rows {monitor_data['feature_range'][0]} to {monitor_data['feature_range'][1]}")
            print(f"  Monitor data: {monitor_data['total_rows']} rows")

        # ----------------------- Drift Detection -----------------
        # Run drift detection if both baseline and monitor data are available
        if baseline_data and monitor_data:
            try:
                # Convert to pandas DataFrames
                baseline_df = pd.DataFrame(baseline_data['feature_data'])
                monitor_df = pd.DataFrame(monitor_data['feature_data'])
                
                # Check if we have enough data
                if len(baseline_df) > 0 and len(monitor_df) > 0:
                    print(f"✓ Running drift detection...")
                    
                    # Prepare metadata for snapshots
                    batch_no = stats.total_batches
                    
                    base_range = baseline_data.get('feature_range', [0, 0])
                    curr_range = monitor_data.get('feature_range', [0, 0])
                    
                    base_win_str = f"rows {base_range[0]} to {base_range[1]}"
                    curr_win_str = f"rows {curr_range[0]} to {curr_range[1]}"
                    
                    # Use actual timestamps from the last rows in each batch for traceability
                    # This shows users exactly when the baseline period ended and current period ended
                    base_ts = baseline_data.get('baseline_feature_timestamp') or baseline_data.get('created_at')
                    curr_ts = monitor_data.get('monitor_feature_timestamp') or datetime.utcnow()
                    
                    # 1. Statistical Drift Detection
                    stat_drift_monitor = InputDataDriftMonitor(
                        project_id=project_id,
                        baseline_data=baseline_df,
                        current_data=monitor_df,
                        batch_no=batch_no,
                        baseline_window_str=base_win_str,
                        current_window_str=curr_win_str,
                        baseline_timestamp=base_ts,
                        current_timestamp=curr_ts
                    )
                    stat_results = await stat_drift_monitor.run()
                    
                    # 2. Model-Based Drift Detection
                    model_drift_monitor = ModelBasedDriftMonitor(
                        project_id=project_id,
                        baseline_data=baseline_df,
                        current_data=monitor_df,
                        baseline_timestamp=base_ts,
                        current_timestamp=curr_ts
                    )
                    model_results = await model_drift_monitor.run()
                    
                    print(f"✓ Drift detection completed")
                else:
                    print(f"⚠ Insufficient data for drift detection")
                    
            except Exception as e:
                print(f"⚠ Drift detection failed: {str(e)}")
                # Don't fail ingestion if drift detection fails
        else:
            print(f"⚠ Baseline or monitor data not available, skipping drift detection")

        await self.db.commit()


        # ---------------  Data Quality Check --------------
        try:
            # Create a background task for quality check
            async def run_quality_check_background():
                """Run data quality checks in background with proper error handling."""
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        # Run quality check
                        checker = DataQualityChecker(project_id)
                        
                        # Get metadata first to get batch info
                        metadata = await checker.get_data_and_metadata()
                        
                        # Run checks separately
                        missing_result = await checker.check_missing_values()
                        duplicate_result = await checker.check_duplicate_rows()
                    
                        async with AsyncSessionLocal() as bg_db:
                            quality_check = DataQualityCheck(
                                project_id=project_id,
                                batch_number=metadata['batch_number'],
                                feature_start_row=metadata['feature_row_range'][0],
                                feature_end_row=metadata['feature_row_range'][1],
                                total_rows_checked=len(metadata['features']) if len(metadata['features']) > 0 else 0,
                                missing_values_summary=missing_result['missing_values'],
                                total_duplicate_rows=duplicate_result.get('total_duplicates', 0),
                                duplicate_percentage=duplicate_result.get('duplicate_percentage', 0.0),
                                total_columns_checked=missing_result.get('total_columns_checked', 0),
                                columns_with_missing=missing_result.get('columns_with_missing', 0),
                                check_status="completed"
                            )
                            bg_db.add(quality_check)
                            await bg_db.commit()
                            print(f"✓ Quality check completed for project {project_id}, batch {metadata['batch_number']}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"⚠ Quality check failed (attempt {retry_count}/{max_retries}): {str(e)}")
                            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                        else:
                            print(f"✗ Quality check failed after {max_retries} attempts: {str(e)}")
                            # Store failed check on final failure
                            try:
                                async with AsyncSessionLocal() as bg_db:
                                    failed_check = DataQualityCheck(
                                        project_id=project_id,
                                        batch_number=stats.total_batches if stats else 0,
                                        check_status="failed",
                                        error_message=str(e)
                                    )
                                    bg_db.add(failed_check)
                                    await bg_db.commit()
                            except Exception as store_error:
                                print(f"⚠ Could not store failed quality check: {str(store_error)}")
            
            # Schedule the background task (fire and forget)
            asyncio.create_task(run_quality_check_background())
            
        except Exception as e:
            # Don't fail ingestion if background task creation fails
            print(f"⚠ Failed to schedule quality check: {str(e)}")

        # Return info for response immediately
        return {"rows_ingested": rows_ingested}

    async def ingest_predictions(
        self,
        project_id: int,
        predictions: list,
        metrics: dict = None,
        model_type: str = None,
        event_time=None,
        metadata=None
    ):
        """
        Ingest predictions and metrics, then run drift detection.
        """
        from app.database import models
        event_time = event_time or datetime.utcnow()
        
        # 1. Store predictions into PredictionOutput
        result = await self.db.execute(
            select(func.max(models.PredictionOutput.row_id)).where(models.PredictionOutput.project_id == project_id)
        )
        max_row_id = result.scalar() or 0
        current_row_id = max_row_id

        if isinstance(predictions, (int, float, str)):
            predictions = [predictions]

        for pred in predictions:
            current_row_id += 1
            pred_row = models.PredictionOutput(
                project_id=project_id,
                row_id=current_row_id,
                prediction=pred,
                created_at=event_time
            )
            self.db.add(pred_row)

        # 2. Update Project Data Stats
        stmt = select(models.ProjectDataStats).where(models.ProjectDataStats.project_id == project_id)
        result = await self.db.execute(stmt)
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = models.ProjectDataStats(project_id=project_id, total_batches=0, last_ingestion_at=event_time)
            self.db.add(stats)
        
        stats.total_batches += 1
        stats.last_ingestion_at = event_time
        stats.latest_prediction_start_row = max_row_id + 1
        stats.latest_prediction_end_row = current_row_id

        # 3. Store provided metrics
        if metrics:
            pred_metrics = models.PredictionMetrics(
                project_id=project_id,
                batch_number=stats.total_batches,
                timestamp=event_time,
                metrics=metrics,
                metadata_info=metadata
            )
            self.db.add(pred_metrics)
            print(f"Stored Metrics for project {project_id}, batch {stats.total_batches}")

        await self.db.flush() # Ensure stats are visible for baseline_mgr
        
        # 4. Update Baseline if needed
        baseline_mgr = BaselineManager(project_id=project_id)
        await baseline_mgr.create_baseline()

        # 5. Drift Detection Logic
        baseline_data = await baseline_mgr.get_baseline_data()

        if baseline_data and baseline_data.get('prediction_data'):
            baseline_preds = baseline_data['prediction_data']
            
            if len(baseline_preds) > 0 and len(predictions) > 0:
                from app.services.prediction_drift import PredictionOutputMonitor
                
                # Run Drift Detection
                monitor = PredictionOutputMonitor(
                    baseline_predictions=np.array(baseline_preds),
                    current_predictions=np.array(predictions),
                    task_type=model_type or "regression"
                )
                drift_results = monitor.run()

                # Store Drift Results
                pred_drift = models.PredictionDrift(
                    project_id=project_id,
                    batch_number=stats.total_batches,
                    timestamp=event_time,
                    baseline_window=f"rows {baseline_data['prediction_range'][0]}-{baseline_data['prediction_range'][1]}",
                    current_window=f"rows {stats.latest_prediction_start_row}-{stats.latest_prediction_end_row}",
                    drift_results={
                        "mean_drift": drift_results.get("mean_drift"),
                        "median_drift": drift_results.get("median_drift"),
                        "variance_drift": drift_results.get("variance_drift"),
                        "quantile_drift": drift_results.get("quantile_drift")
                    },
                    ks_test=drift_results.get("ks_test"),
                    psi=drift_results.get("psi"),
                    alerts=drift_results.get("alerts"),
                    overall_drift=len(drift_results.get("alerts", [])) > 0
                )
                self.db.add(pred_drift)
                print(f"Prediction Drift Detection completed for project {project_id}, batch {stats.total_batches}")
            else:
                print(f"Insufficient data for prediction drift detection in project {project_id}")
        else:
            print(f"No baseline found for prediction drift detection in project {project_id}")

        await self.db.commit()
            
        return {"predictions_processed": len(predictions), "metrics_received": bool(metrics), "batch_number": stats.total_batches}
