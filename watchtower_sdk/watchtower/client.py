import requests
from .exceptions import WatchtowerSDKError


class HTTPClient:
    """
    HTTP client for communicating with Watchtower API.
    Handles authentication and error management.
    """
    
    def __init__(self, api_key: str, endpoint: str, timeout: int = 30):
        """
        Initialize HTTP client.
        
        Args:
            api_key: API key for authentication
            endpoint: Base URL for the API
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout = timeout

    def post(self, path: str, payload: dict) -> dict:
        """
        Send POST request to API endpoint.
        
        Args:
            path: Endpoint path
            payload: Request payload dictionary
            
        Returns:
            dict: JSON response from server
            
        Raises:
            WatchtowerSDKError: If request fails
        """
        url = f"{self.endpoint}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
            
        except requests.exceptions.Timeout:
            raise WatchtowerSDKError(f"Request timeout after {self.timeout}s: {url}")
            
        except requests.exceptions.ConnectionError as e:
            raise WatchtowerSDKError(f"Connection error: {str(e)}")
            
        except requests.exceptions.HTTPError as e:
            # Include response details for debugging
            error_msg = f"HTTP {e.response.status_code}: {e.response.reason}"
            try:
                error_detail = e.response.json()
                error_msg += f" | {error_detail}"
            except:
                error_msg += f" | {e.response.text}"
            raise WatchtowerSDKError(error_msg)
            
        except requests.exceptions.RequestException as e:
            raise WatchtowerSDKError(f"Request failed: {str(e)}")
