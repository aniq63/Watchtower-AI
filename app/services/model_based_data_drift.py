import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sqlalchemy import select
from app.database import models
from app.database.connection import AsyncSessionLocal
from app.constants import (
    MODEL_BASED_DRIFT_THRESHOLD,
    MODEL_RF_N_ESTIMATORS,
    MODEL_RF_RANDOM_STATE,
    MODEL_RF_TEST_SIZE
)


class ModelBasedDriftMonitor:
    """
    Model-based drift detection using RandomForest classifier.
    Trains a model to distinguish between baseline and current data.
    High accuracy indicates significant drift.
    """
    
    def __init__(
        self,
        project_id: int,
        baseline_data: pd.DataFrame,
        current_data: pd.DataFrame,
        baseline_timestamp=None,
        current_timestamp=None,
        alert_threshold: float = None,
        test_size: float = 0.2,
        random_state: int = 42,
    ):
        """
        Initialize the model-based drift monitor.
        
        Args:
            project_id: Project ID for database storage
            baseline_data: Baseline feature data
            current_data: Current/monitor feature data
            alert_threshold: Accuracy threshold for alert (loaded from config if None)
            test_size: Proportion of data for testing
            random_state: Random seed for reproducibility
        """
        self.project_id = project_id
        self.baseline_data = baseline_data.copy()
        self.current_data = current_data.copy()
        
        # Source timestamps
        self.baseline_timestamp = baseline_timestamp
        self.current_timestamp = current_timestamp
        
        self.alert_threshold = alert_threshold
        self.test_size = test_size
        self.random_state = random_state

        self.model = RandomForestClassifier(
            n_estimators=MODEL_RF_N_ESTIMATORS,
            random_state=MODEL_RF_RANDOM_STATE,
            n_jobs=-1
        )
        
        self.results = None

    async def load_config(self):
        """Load alert threshold from DataDriftConfig."""
        if self.alert_threshold is not None:
            return  # Already set
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(models.DataDriftConfig).where(
                    models.DataDriftConfig.project_id == self.project_id
                )
            )
            config = result.scalars().first()
            
            if config:
                # Load model-based drift threshold from config
                self.alert_threshold = config.model_based_drift_threshold
            else:
                # Default from constants if no config found
                self.alert_threshold = MODEL_BASED_DRIFT_THRESHOLD

    def _build_training_data(self):
        """
        Build training data by labeling baseline as 0 and current as 1.
        Returns train/test split.
        """
        # Select only numeric columns to avoid issues with dates/strings
        numeric_cols = self.baseline_data.select_dtypes(include=[np.number]).columns
        
        baseline_numeric = self.baseline_data[numeric_cols].copy()
        current_numeric = self.current_data[numeric_cols].copy()
        
        # Add source labels
        baseline_numeric["__source__"] = 0
        current_numeric["__source__"] = 1

        # Combine datasets
        df = pd.concat([baseline_numeric, current_numeric], axis=0)
        df = df.reset_index(drop=True)
        
        # Handle NaN values (fill with 0 or mean? RandomForest can't handle NaN in some versions, but sklearn 1.8 might)
        # For safety/consistency, fillna(0) or dropna
        df = df.fillna(0)

        # Separate features and labels
        X = df.drop(columns="__source__")
        y = df["__source__"]

        # Train/test split
        return train_test_split(
            X,
            y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y
        )

    def detect_drift(self) -> dict:
        """
        Run drift detection using RandomForest classifier.
        Returns drift score and alert status.
        """
        X_train, X_test, y_train, y_test = self._build_training_data()

        # Train model
        self.model.fit(X_train, y_train)
        
        # Predict on test set
        y_pred = self.model.predict(X_test)

        # Calculate accuracy
        accuracy = accuracy_score(y_test, y_pred)
        
        # Determine if alert should be triggered
        alert = bool(accuracy >= self.alert_threshold)

        self.results = {
            "drift_score": float(accuracy),
            "alert": alert,
            "alert_threshold": self.alert_threshold,
            "baseline_samples": len(self.baseline_data),
            "current_samples": len(self.current_data),
            "test_accuracy": float(accuracy)
        }
        
        return self.results

    async def store_results(self):
        """Store model-based drift detection results in database."""
        if self.results is None:
            raise ValueError("No results to store. Run detect_drift() first.")
        
        async with AsyncSessionLocal() as db:
            try:
                drift_record = models.ModelBasedDrift(
                    project_id=self.project_id,
                    drift_score=self.results["drift_score"],
                    alert_triggered=self.results["alert"],
                    alert_threshold=self.results["alert_threshold"],
                    baseline_samples=self.results["baseline_samples"],
                    current_samples=self.results["current_samples"],
                    baseline_source_timestamp=self.baseline_timestamp,
                    current_source_timestamp=self.current_timestamp,
                    model_type="RandomForest",
                    test_accuracy=self.results["test_accuracy"]
                )
                
                db.add(drift_record)
                await db.commit()
                
                print(f"✓ Model-based drift detection results stored for project {self.project_id}")
                print(f"  Drift Score: {self.results['drift_score']:.4f}")
                print(f"  Alert Threshold: {self.results['alert_threshold']:.4f}")
                
                if self.results["alert"]:
                    print(f"⚠ MODEL-BASED DRIFT ALERT: Accuracy {self.results['drift_score']:.4f} >= {self.results['alert_threshold']:.4f}")
                else:
                    print(f"✓ No significant drift detected")
                
            except Exception as e:
                await db.rollback()
                print(f"Error storing model-based drift results: {str(e)}")
                raise

    async def run(self) -> dict:
        """
        Run complete model-based drift detection workflow.
        Loads config, detects drift, and stores results.
        """
        # Load configuration
        await self.load_config()
        
        # Detect drift
        results = self.detect_drift()
        
        # Store results
        await self.store_results()
        
        return results
