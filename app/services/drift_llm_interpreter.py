"""
Drift Interpretation & Explanation Engine using GROQ LLM.
Provides comprehensive analysis, interpretation, and recommendations for drift detection results.
Implements singleton pattern for efficient LLM client management.
"""
import json
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from warnings import filterwarnings

from app.config import get_settings

filterwarnings("ignore")

settings = get_settings()

# Singleton LLM client
_drift_llm_client = None


def get_drift_llm_client() -> ChatGroq:
    """Get singleton LLM client for drift interpretation."""
    global _drift_llm_client
    if _drift_llm_client is None:
        groq_key = getattr(settings, 'groq_api_key', None)
        if not groq_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        _drift_llm_client = ChatGroq(
            model_name="openai/gpt-oss-20b",  # Fast, powerful model
            api_key=groq_key,
            temperature=0.7,
            max_tokens=1024
        )
    return _drift_llm_client


def _format_feature_stats(feature_stats: Dict[str, Any]) -> str:
    """Format feature statistics for LLM input."""
    formatted = []
    for feature, stats in feature_stats.items():
        if stats.get("baseline"):
            baseline = stats["baseline"]
            formatted.append(
                f"  - {feature}: Mean={baseline.get('mean', 'N/A')}, "
                f"Median={baseline.get('median', 'N/A')}, "
                f"Std={baseline.get('std', 'N/A')}"
            )
    return "\n".join(formatted)


def _format_drift_tests(drift_tests: Dict[str, Any]) -> str:
    """Format drift test results for LLM input."""
    formatted = []
    for feature, tests in drift_tests.items():
        formatted.append(f"\n  {feature}:")
        for test_name, test_result in tests.items():
            if isinstance(test_result, dict):
                if "drift_detected" in test_result:
                    status = "🔴 DRIFT" if test_result["drift_detected"] else "🟢 No Drift"
                    formatted.append(f"    - {test_name}: {status} (Value: {test_result.get('value', test_result.get('p_value', 'N/A'))})")
                elif "severity" in test_result:
                    formatted.append(f"    - {test_name}: Severity={test_result['severity']} (Value: {test_result.get('value', 'N/A')})")
    return "\n".join(formatted)


async def interpret_data_drift(
    project_id: int,
    drift_snapshot: Dict[str, Any],
    baseline_window: str,
    current_window: str
) -> str:
    """
    Interpret input data drift detection results using LLM.
    
    Args:
        project_id: Project identifier
        drift_snapshot: Contains feature_stats, drift_tests, alerts, overall_drift, drift_score
        baseline_window: Baseline data window description
        current_window: Current data window description
        
    Returns:
        LLM-generated interpretation and recommendations
    """
    
    def create_fallback_message() -> str:
        """Fallback message when LLM fails."""
        alert_count = len(drift_snapshot.get("alerts", []))
        drift_score = drift_snapshot.get("drift_score", 0)
        return (
            f"Data Drift Analysis: Detected {alert_count} features with drift signals. "
            f"Overall drift score: {drift_score:.2%}. "
            f"Baseline window: {baseline_window}. Current window: {current_window}. "
            f"Review the drift_tests and feature_stats for detailed information."
        )
    
    try:
        llm = get_drift_llm_client()
    except Exception as e:
        print(f"Failed to initialize LLM: {str(e)}")
        return create_fallback_message()
    
    feature_stats_str = _format_feature_stats(drift_snapshot.get("feature_stats", {}))
    drift_tests_str = _format_drift_tests(drift_snapshot.get("drift_tests", {}))
    alerts = drift_snapshot.get("alerts", [])
    drift_score = drift_snapshot.get("drift_score", 0)
    overall_drift = drift_snapshot.get("overall_drift", False)
    
    system_prompt_template = """You are a data quality and drift detection expert. 
Analyze the following drift detection results and provide:

1. **INTERPRETATION**: What do the drift signals mean? Which features are drifting and why?
2. **SEVERITY ASSESSMENT**: Is this drift expected, concerning, or critical?
3. **ROOT CAUSE ANALYSIS**: What could cause this drift pattern?
4. **RECOMMENDATIONS**: What actions should be taken?
5. **NEXT STEPS**: What monitoring or investigation should follow?

### DRIFT DETECTION RESULTS:

**Baseline Window:** {baseline_window}
**Current Window:** {current_window}
**Overall Drift Detected:** {overall_drift}
**Drift Score (% features with alerts):** {drift_score:.1%}
**Alerted Features:** {alerts}

**Feature Statistics:**
{feature_stats}

**Drift Tests Results:**
{drift_tests}

---

### ANALYSIS GUIDELINES:
- Focus on FACTS from the test results, not speculation
- Explain what each drift signal means in business context
- Consider patterns across multiple features
- Provide actionable recommendations
- Keep analysis concise but thorough (max 400 words)

Generate the analysis now:
"""
    
    prompt = PromptTemplate(
        template=system_prompt_template,
        input_variables=[
            "baseline_window", "current_window", "overall_drift", "drift_score",
            "alerts", "feature_stats", "drift_tests"
        ]
    )
    
    try:
        chain = prompt | llm
        
        result = chain.invoke({
            "baseline_window": baseline_window,
            "current_window": current_window,
            "overall_drift": overall_drift,
            "drift_score": drift_score,
            "alerts": ", ".join(alerts) if alerts else "None",
            "feature_stats": feature_stats_str,
            "drift_tests": drift_tests_str
        })
        
        return str(result.content) if hasattr(result, 'content') else str(result)
    
    except Exception as e:
        print(f"Error generating drift interpretation: {str(e)}")
        return create_fallback_message()


async def interpret_prediction_drift(
    project_id: int,
    drift_results: Dict[str, Any],
    task_type: str,
    baseline_window: str,
    current_window: str
) -> str:
    """
    Interpret prediction output drift detection results using LLM.
    
    Args:
        project_id: Project identifier
        drift_results: Contains mean_drift, median_drift, variance_drift, ks_test, psi, alerts
        task_type: "regression" or "classification"
        baseline_window: Baseline prediction window description
        current_window: Current prediction window description
        
    Returns:
        LLM-generated interpretation and recommendations
    """
    
    def create_fallback_message() -> str:
        """Fallback message when LLM fails."""
        alerts = drift_results.get("alerts", [])
        return (
            f"Prediction Drift Analysis (Task: {task_type}): "
            f"Detected {len(alerts)} alert signals. "
            f"Baseline: {baseline_window}. Current: {current_window}. "
            f"Review mean_drift, median_drift, variance_drift, and PSI metrics for details."
        )
    
    try:
        llm = get_drift_llm_client()
    except Exception as e:
        print(f"Failed to initialize LLM: {str(e)}")
        return create_fallback_message()
    
    # Format drift results
    drift_summary = []
    if drift_results.get("mean_drift"):
        drift_summary.append(f"Mean Drift: {drift_results['mean_drift']:.4f}")
    if drift_results.get("median_drift"):
        drift_summary.append(f"Median Drift: {drift_results['median_drift']:.4f}")
    if drift_results.get("variance_drift"):
        drift_summary.append(f"Variance Drift: {drift_results['variance_drift']:.4f}")
    
    ks_test = drift_results.get("ks_test", {})
    psi = drift_results.get("psi", {})
    alerts = drift_results.get("alerts", [])
    
    system_prompt_template = """You are a machine learning model monitoring expert.
Analyze the following prediction drift detection results and provide:

1. **INTERPRETATION**: What does this drift mean for model performance?
2. **SEVERITY ASSESSMENT**: How critical is this drift?
3. **IMPACT ANALYSIS**: How might this affect predictions/business outcomes?
4. **ROOT CAUSE HYPOTHESIS**: Why might this drift be occurring?
5. **RECOMMENDATIONS**: What actions should be taken?

### PREDICTION DRIFT DETECTION RESULTS:

**Task Type:** {task_type}
**Baseline Window:** {baseline_window}
**Current Window:** {current_window}

**Drift Metrics:**
{drift_summary}

**KS Test:**
  - Statistic: {ks_stat}
  - P-Value: {ks_pval}
  - Drift Detected: {ks_drift}

**PSI (Population Stability Index):**
  - Value: {psi_val}
  - Severity: {psi_severity}

**Alert Signals:** {alerts}

---

### ANALYSIS GUIDELINES:
- For regression: Focus on output distribution shifts, mean/variance changes
- For classification: Focus on class probability shifts, class imbalance changes
- Explain business impact of the drift
- Consider if model retraining might be necessary
- Suggest monitoring thresholds or action items
- Keep analysis concise but actionable (max 400 words)

Generate the analysis now:
"""
    
    prompt = PromptTemplate(
        template=system_prompt_template,
        input_variables=[
            "task_type", "baseline_window", "current_window", "drift_summary",
            "ks_stat", "ks_pval", "ks_drift", "psi_val", "psi_severity", "alerts"
        ]
    )
    
    try:
        chain = prompt | llm
        
        result = chain.invoke({
            "task_type": task_type,
            "baseline_window": baseline_window,
            "current_window": current_window,
            "drift_summary": "\n  ".join(drift_summary) if drift_summary else "No significant drift detected in basic metrics",
            "ks_stat": ks_test.get("ks_stat", "N/A"),
            "ks_pval": ks_test.get("p_value", "N/A"),
            "ks_drift": ks_test.get("drift", "N/A"),
            "psi_val": psi.get("psi", "N/A"),
            "psi_severity": psi.get("severity", "N/A"),
            "alerts": ", ".join(alerts) if alerts else "None"
        })
        
        return str(result.content) if hasattr(result, 'content') else str(result)
    
    except Exception as e:
        print(f"Error generating prediction drift interpretation: {str(e)}")
        return create_fallback_message()
