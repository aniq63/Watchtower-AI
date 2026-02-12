# Watchtower AI SDK

**The official Python client for [Watchtower AI](https://github.com/aniq63/Watchtower-AI).**

Watchtower AI is a comprehensive observability platform for your data pipelines and machine learning models. It helps you detect **data drift**, monitor **data quality**, and evaluate **LLM performance** in real-time.

---

## 🚀 Key Features

*   **Data Drift Detection**: Automatically detect distribution shifts in your tabular data (KS tests, PSI, etc.).
*   **Data Quality Monitoring**: Validate schema, check for nulls, duplicates, and ranges.
*   **LLM Observability**: Monitor token usage, toxicity, and response quality for your GenAI applications.
*   **Async Logging**: Low-latency, non-blocking API calls designed for high-throughput production environments.
*   **Cloud Ready**: Optimized for deployment on Render, AWS, and other cloud providers.

---

## 📦 Installation

```bash
pip install watchtower-sdk
```

---

## ⚙️ Configuration

The SDK is designed to be **Zero-Config** in production. It automatically reads from environment variables.

### Environment Variables (Recommended)
Set these in your local terminal or your cloud provider's dashboard (e.g., Render Environment Variables):

```bash
# Your Project API Key (Required)
export WATCHTOWER_API_KEY="your_project_api_key_here"

# Your Watchtower Backend URL (Required for Cloud)
# Defaults to http://localhost:8000 if not set
export WATCHTOWER_API_URL="https://your-watchtower-app.onrender.com"
```

---

## 🛠️ Usage Examples

### 1. Monitoring Tabular Data (ML Models)
Perfect for validating training data or inference batches.

```python
import pandas as pd
from watchtower.monitor import WatchtowerInputMonitor

# Initialize (reads env vars automatically)
monitor = WatchtowerInputMonitor(project_name="Credit Scoring v1")

# Load your production data
df = pd.read_csv("inference_batch.csv")

# Log data to Watchtower
# This sends the data asynchronously to your backend
response = monitor.log(df)

print(f"Logged {len(df)} rows. Status: {response}")
```

### 2. Monitoring LLMs (GenAI)
Track prompts, responses, and token usage.

```python
from watchtower.llm_monitor import WatchtowerLLMMonitor

# Initialize
llm_monitor = WatchtowerLLMMonitor(project_name="Customer Support Bot")

# Log an interaction
llm_monitor.log(
    input_text="How do I reset my password?",
    output_text="You can reset your password by clicking 'Forgot Password' on the login page.",
    metadata={
        "model": "gpt-4",
        "latency_ms": 450,
        "user_id": "user_123"
    }
)
```

---

## ☁️ Cloud Deployment (Render/Railway)

If you are hosting your own Watchtower Backend on Render:

1.  **Deploy Backend**: Follow the [Deployment Guide](https://github.com/aniq63/Watchtower-AI/blob/main/DEPLOYMENT_GUIDE.md).
2.  **Get URL**: Copy your backend URL (e.g., `https://my-app.onrender.com`).
3.  **Set Env Var**: Set `WATCHTOWER_API_URL` to that URL in your production environment.
4.  **Run**: Your code works exactly the same as it did locally!

---

## 🛡️ License

This project is licensed under the MIT License.
