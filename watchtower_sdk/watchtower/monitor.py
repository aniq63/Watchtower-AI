from .client import HTTPClient
from .serializer import serialize_features
from .exceptions import WatchtowerSDKError
from datetime import datetime

class WatchtowerInputMonitor:
    """
    Main SDK object for data monitoring.
    Handles logging features to Watchtower AI backend for validation and drift detection.
    """

    def __init__(self, api_key: str, project_name: str, endpoint: str):
        self.api_key = api_key
        self.project_name = project_name
        self.endpoint = endpoint.rstrip("/")  # remove trailing slash
        self.client = HTTPClient(api_key=self.api_key, endpoint=self.endpoint)

    def log(
        self,
        features,
        stage: str = "model_input",
        event_time: datetime = None,
        metadata: dict = None
    ):
        """
        Send feature data to backend for monitoring.
        
        Args:
            features: Feature data (dict, list, DataFrame, etc.)
            stage: Monitoring stage (default: "model_input")
            event_time: Event timestamp (default: current UTC time)
            metadata: Additional metadata (optional)
        """
        if features is None:
            raise WatchtowerSDKError("Features cannot be None")

        # Handle event_time serialization
        if event_time is None:
            event_time_str = datetime.utcnow().isoformat()
        elif isinstance(event_time, datetime):
            event_time_str = event_time.isoformat()
        else:
            event_time_str = str(event_time)

        payload = {
            "project_name": self.project_name,
            "event_time": event_time_str,
            "features": serialize_features(features),
            "stage": stage,
            "metadata": metadata or {}
        }

        # Send data to backend
        try:
            response = self.client.post("/ingest", payload)
            return response
        except Exception as e:
            raise WatchtowerSDKError(f"Failed to log data: {e}")


class WatchtowerModelMonitor:
    """
    SDK object for model prediction & metric monitoring.
    """

    def __init__(self, api_key: str, project_name: str, endpoint: str, model_type: str = None):
        self.api_key = api_key
        self.project_name = project_name
        self.endpoint = endpoint.rstrip("/")
        self.model_type = model_type  # "classification" or "regression"
        self.client = HTTPClient(api_key=self.api_key, endpoint=self.endpoint)

    def log(
        self,
        predictions,
        metadata: dict = None,
        # Classification metrics
        accuracy: float = None,
        precision: float = None,
        recall: float = None,
        f1_score: float = None,
        roc_auc: float = None,
        # Regression metrics
        mae: float = None,
        mse: float = None,
        rmse: float = None,
        r2_score: float = None
    ):
        """
        Send predictions and/or metrics to backend.
        
        Args:
            predictions: List/Array of prediction values
            metadata: Additional metadata (batch info, environment, etc.)
            accuracy: Accuracy score (0-1)
            precision: Precision score (0-1)
            recall: Recall score (0-1)
            f1_score: F1 score (0-1)
            roc_auc: ROC AUC score (0-1)
            mae: Mean Absolute Error
            mse: Mean Squared Error
            rmse: Root Mean Squared Error
            r2_score: R-squared score
        """
        # Serialize predictions
        serialized_preds = serialize_features(predictions)
        
        # Construct metrics dictionary from explicit arguments
        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "roc_auc": roc_auc,
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "r2_score": r2_score
        }
        # Filter out None values
        metrics = {k: v for k, v in metrics.items() if v is not None}
        
        # Serialize metrics just in case (e.g. numpy floats)
        serialized_metrics = {}
        if metrics:
            serialized_metrics = serialize_features(metrics)
            # serialize_features returns a list of dicts for dict input, slice index 0
            if isinstance(serialized_metrics, list) and len(serialized_metrics) > 0:
                serialized_metrics = serialized_metrics[0]

        payload = {
            "project_name": self.project_name,
            "event_time": datetime.utcnow().isoformat(),
            "predictions": serialized_preds,
            "metrics": serialized_metrics,
            "model_type": self.model_type,
            "metadata": metadata or {}
        }

        try:
            # We use a new endpoint for predictions/metrics
            response = self.client.post("/ingest/predictions", payload)
            return response
        except Exception as e:
            raise WatchtowerSDKError(f"Failed to log model data: {e}")
