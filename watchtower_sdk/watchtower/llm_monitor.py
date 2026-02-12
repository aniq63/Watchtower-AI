"""
Watchtower LLM Monitor SDK - Client-side class for logging LLM interactions
"""
from .client import HTTPClient
from .exceptions import WatchtowerSDKError
from datetime import datetime


class WatchtowerLLMMonitor:
    """
    SDK class for monitoring LLM interactions.
    Logs input/response pairs and sends them to Watchtower backend for analysis.
    """

    def __init__(self, api_key: str, project_name: str, endpoint: str = "http://localhost:8000", timeout: int = 60):
        """
        Initialize the LLM Monitor.
        
        Args:
            api_key: API key for authentication
            project_name: Name of the project
            endpoint: Base URL of Watchtower API (default: localhost:8000)
            timeout: Request timeout in seconds (default: 60)
        """
        self.api_key = api_key
        self.project_name = project_name
        self.endpoint = endpoint.rstrip("/")
        self.client = HTTPClient(api_key=self.api_key, endpoint=self.endpoint, timeout=timeout)

    def log_interaction(
        self,
        input_text: str,
        response_text: str,
        metadata: dict = None
    ) -> dict:
        """
        Log an LLM interaction.
        
        Args:
            input_text: Input text sent to the LLM
            response_text: Response received from the LLM
            metadata: Optional metadata dictionary
            
        Returns:
            dict: Response from backend with logged interaction details
            
        Raises:
            WatchtowerSDKError: If request fails
        """
        if not input_text:
            raise WatchtowerSDKError("input_text cannot be empty")
        
        if not response_text:
            raise WatchtowerSDKError("response_text cannot be empty")

        payload = {
            "project_name": self.project_name,
            "input_text": input_text,
            "response_text": response_text,
            "event_time": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        try:
            response = self.client.post("/llm/ingest", payload)
            return response
        except Exception as e:
            raise WatchtowerSDKError(f"Failed to log LLM interaction: {e}")
