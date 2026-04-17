<p align="center">
  <img src="images/Gemini_Generated_Image_dwfkm4dwfkm4dwfk.png" alt="Watchtower AI Logo" width="280"/>
</p>

<h1 align="center">Watchtower AI</h1>

<p align="center">
  <strong>A comprehensive ML & LLM observability platform for production systems.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/watchtower-sdk/0.1.1/">
    <img src="https://img.shields.io/pypi/v/watchtower-sdk?color=orange&label=PyPI&logo=pypi&logoColor=white" alt="PyPI Version">
  </a>
  <a href="https://watchtower-ai-production-604f.up.railway.app">
    <img src="https://img.shields.io/badge/Live%20Demo-Railway-0b0d0e?logo=railway&logoColor=white" alt="Live Demo">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
  </a>
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI">
</p>

---

## 🔭 What is Watchtower AI?

Watchtower AI is a **self-hosted monitoring framework** designed to track model performance, data drift, data quality, and LLM behavior in real-time. It provides actionable insights through an integrated dashboard, enabling data-driven decisions for model retraining and maintenance in production environments.

> **Think of it as Datadog, but specifically built for ML pipelines and LLM applications.**

### 🌐 Live Demo

👉 **[https://watchtower-ai-production-604f.up.railway.app](https://watchtower-ai-production-604f.up.railway.app)**

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📊 **Data Drift Detection** | Detect distribution shifts using KS Test, PSI, Mean/Median/Variance Shift, and Model-Based drift detection. |
| 🧪 **Data Quality Monitoring** | Validate schema, detect missing values, and identify duplicate records automatically. |
| 📈 **Prediction Monitoring** | Track classification (accuracy, precision, recall, F1, AUC) and regression (MAE, MSE, RMSE, R²) metrics over time. |
| 🤖 **LLM Observability** | Monitor prompt-response pairs, detect toxicity, track token usage, and evaluate response quality with an LLM Judge. |
| 🧠 **AI-Powered Insights** | Get natural language interpretations of drift results powered by LLM analysis. |
| ⚡ **Real-Time Alerting** | Configurable thresholds trigger alerts when drift or quality issues exceed limits. |
| 📉 **Interactive Dashboard** | Visualize trends, drill into per-feature drift snapshots, and compare baseline vs. production distributions. |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Watchtower AI Platform                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Frontend    │  │   FastAPI    │  │  PostgreSQL  │      │
│  │  (Jinja2 +   │──│   Backend    │──│  (Supabase / │      │
│  │   Vanilla JS) │  │   Engine    │  │   Render DB) │      │
│  └──────────────┘  └──────┬───────┘  └──────────────┘      │
│                           │                                  │
│           ┌───────────────┼───────────────┐                  │
│           │               │               │                  │
│   ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼───────┐         │
│   │  Data Drift  │ │ Prediction  │ │    LLM      │         │
│   │  Detection   │ │ Monitoring  │ │ Monitoring  │         │
│   │  Service     │ │ Service     │ │ Service     │         │
│   └──────────────┘ └─────────────┘ └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Python SDK (pip install)                   │
├──────────────┬──────────────────┬────────────────────────────┤
│ InputMonitor │  ModelMonitor    │  LLMMonitor                │
│ (Tabular)    │  (Predictions)   │  (Prompt/Response)         │
└──────────────┴──────────────────┴────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Install the SDK

```bash
pip install watchtower-sdk
```

### 2. Monitor Your Data

```python
import pandas as pd
from watchtower.monitor import WatchtowerInputMonitor

monitor = WatchtowerInputMonitor(
    project_name="My ML Project",
    api_key="your_project_api_key",
    endpoint="https://watchtower-ai-production-604f.up.railway.app"
)

df = pd.read_csv("production_data.csv")
response = monitor.log(df)
print(response)
```

### 3. Monitor Model Predictions

```python
from watchtower.monitor import WatchtowerModelMonitor

model_monitor = WatchtowerModelMonitor(
    project_name="Fraud Detector",
    api_key="your_project_api_key",
    endpoint="https://watchtower-ai-production-604f.up.railway.app",
    model_type="classification"
)

model_monitor.log(
    predictions=[0, 1, 0, 0, 1, 1, 0, 1],
    accuracy=0.92,
    precision=0.89,
    recall=0.95,
    f1_score=0.91,
    roc_auc=0.96
)
```

### 4. Monitor LLM Applications

```python
from watchtower.llm_monitor import WatchtowerLLMMonitor

llm_monitor = WatchtowerLLMMonitor(
    api_key="your_api_key",
    project_name="Customer Support Bot",
    endpoint="https://watchtower-ai-production-604f.up.railway.app"
)

llm_monitor.log_interaction(
    input_text="How do I reset my password?",
    response_text="Go to Settings > Security > Reset Password.",
    metadata={"model": "gpt-4", "latency_ms": 320}
)
```

---

## 📊 Drift Detection Tests

Watchtower runs **6 statistical tests** on every monitoring snapshot:

| Test | Type | What It Detects |
|---|---|---|
| **Mean Shift** | Statistical | Change in central tendency ( >10% relative change) |
| **Median Shift** | Statistical | Robust central tendency change (outlier resistant) |
| **Variance Shift** | Statistical | Change in data spread/dispersion ( >20% relative change) |
| **KS Test** | Distribution | Full distribution comparison (p-value < 0.05) |
| **PSI** | Distribution | Population stability (Low < 0.1, Moderate 0.1–0.25, High > 0.25) |
| **Model-Based** | ML | RandomForest classifier distinguishes baseline from current data |

All thresholds are **configurable per-project** via the dashboard.

---

## 🛠️ Self-Hosting

### Prerequisites

- Python 3.8+
- PostgreSQL database (Supabase, Render DB, or any PostgreSQL instance)
- A Groq API key (for LLM-powered insights)

### Local Development

```bash
# Clone the repository
git clone https://github.com/aniq63/Watchtower-AI.git
cd Watchtower-AI

# Create virtual environment
python -m venv .myenv
.myenv\Scripts\activate   # Windows
# source .myenv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment variables
set GROQ_API_KEY=your_groq_key
set DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Run the server
uvicorn main:app --reload
```

### Docker

```bash
docker-compose up --build
```

### Deploy to Railway

1. Push your code to GitHub.
2. Create a new **Web Service** on [Railway](https://railway.app).
3. Connect your GitHub repository.
4. Set environment variables (`DATABASE_URL`, `GROQ_API_KEY`).
5. Railway will auto-build from the `Dockerfile` and deploy.

---

## 📁 Project Structure

```
Watchtower-AI/
├── app/
│   ├── config.py                 # Environment & settings
│   ├── constants.py              # Default thresholds & configs
│   ├── database/                 # SQLAlchemy models & connection
│   ├── routes/                   # FastAPI route handlers
│   │   ├── ingest.py             # Data ingestion endpoint
│   │   ├── drift_detection.py    # Drift analysis endpoints
│   │   ├── data_quality.py       # Quality check endpoints
│   │   ├── prediction_monitoring.py
│   │   └── llm_monitoring.py
│   └── services/                 # Core business logic
│       ├── feature_monitoring/   # Drift detection engine
│       ├── prediction_monitoring/# Prediction drift analysis
│       └── llm_monitoring/       # LLM evaluation engine
├── frontend/
│   ├── templates/                # Jinja2 HTML templates
│   └── static/                   # CSS, JS, assets
├── watchtower_sdk/               # Python SDK (published to PyPI)
│   └── watchtower/
│       ├── client.py             # HTTP client
│       ├── monitor.py            # InputMonitor + ModelMonitor
│       └── llm_monitor.py        # LLMMonitor
├── Dockerfile                    # Production container
├── docker-compose.yml            # Local dev orchestration
├── requirements.txt              # Python dependencies
└── main.py                       # FastAPI entrypoint
```

---

## 📦 SDK Reference

| SDK Class | Purpose | Endpoint |
|---|---|---|
| `WatchtowerInputMonitor` | Log tabular/feature data | `/ingest` |
| `WatchtowerModelMonitor` | Log predictions & metrics | `/ingest/predictions` |
| `WatchtowerLLMMonitor` | Log LLM prompt-response pairs | `/llm/ingest` |

**Full documentation:** [https://watchtower-ai-production-604f.up.railway.app/documentation](https://watchtower-ai-production-604f.up.railway.app/documentation)

**PyPI Package:** [https://pypi.org/project/watchtower-sdk/](https://pypi.org/project/watchtower-sdk/0.1.1/)

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Uvicorn, SQLAlchemy (async) |
| **Database** | PostgreSQL (asyncpg), Supabase compatible |
| **Frontend** | Jinja2, Vanilla JS, CSS |
| **ML/Stats** | Pandas, NumPy, SciPy, Scikit-learn |
| **LLM** | LangChain, Groq, Detoxify |
| **Deployment** | Docker, Railway.app |
| **SDK** | Published on PyPI |

---

## 🤝 Contributing

Watchtower AI is **open-source** and we welcome contributions from the community! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Ways to Contribute

- � **Bug Reports** — Found a bug? Open an [issue](https://github.com/aniq63/Watchtower-AI/issues).
- 💡 **Feature Requests** — Have an idea? Start a [discussion](https://github.com/aniq63/Watchtower-AI/issues).
- 📝 **Documentation** — Improve docs, fix typos, add examples.
- 🧪 **Tests** — Add unit tests or integration tests.
- 🔧 **Code** — Fix bugs, optimize performance, or add new drift detection algorithms.

All contributions, big or small, are greatly appreciated! ⭐

---

## �📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Muhammad Aniq Ramzan**

- 📧 Email: [aniqramzan5758@gmail.com](mailto:aniqramzan5758@gmail.com)
- GitHub: [@aniq63](https://github.com/aniq63)

---

<p align="center">
  <strong>Built with ❤️ for the ML community</strong>
</p>
