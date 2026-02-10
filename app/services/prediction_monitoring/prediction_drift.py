import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sqlalchemy import select
from datetime import datetime
from typing import Optional, Dict, Any
from app.database import models
from app.database.connection import AsyncSessionLocal
from app.services.feature_monitoring.drift_llm_interpreter import interpret_prediction_drift

class PredictionOutputMonitor:
    def __init__(
        self,
        project_id: int,
        baseline_predictions,
        current_predictions,
        task_type="regression",  # "regression" or "classification"
        batch_no: Optional[int] = None,
        baseline_window_str: str = "unknown",
        current_window_str: str = "unknown",
        baseline_timestamp: Optional[datetime] = None,
        current_timestamp: Optional[datetime] = None,
        quantiles=(0.25, 0.5, 0.75, 0.95),
        mean_threshold=0.1,
        median_threshold=0.1,
        variance_threshold=0.2,
        ks_threshold=0.1,
        psi_bins=10,
        psi_thresholds=(0.1, 0.25),
        min_samples=50
    ):
        """
        Args:
            project_id: Project ID for database storage
            baseline_predictions: np.ndarray or pd.DataFrame/Series of model predictions from baseline
            current_predictions: same as baseline, production predictions
            task_type: "regression" or "classification"
            batch_no: Optional batch number
            baseline_window_str: Baseline time window description
            current_window_str: Current time window description
            baseline_timestamp: Baseline timestamp
            current_timestamp: Current timestamp
            thresholds: for drift detection in each metric
            psi_bins: number of bins for PSI calculation
            psi_thresholds: (low, high) drift levels
            min_samples: skip monitoring if sample size too small
        """
        # Project and batch info
        self.project_id = project_id
        self.batch_no = batch_no
        self.baseline_window = baseline_window_str
        self.current_window = current_window_str
        self.baseline_timestamp = baseline_timestamp
        self.current_timestamp = current_timestamp
        
        # Convert to DataFrame if numpy
        if isinstance(baseline_predictions, np.ndarray):
            baseline_predictions = pd.DataFrame(baseline_predictions, columns=["pred"])
        if isinstance(current_predictions, np.ndarray):
            current_predictions = pd.DataFrame(current_predictions, columns=["pred"])

        self.baseline = baseline_predictions
        self.current = current_predictions
        self.task_type = task_type
        self.quantiles = quantiles
        self.mean_threshold = mean_threshold
        self.median_threshold = median_threshold
        self.variance_threshold = variance_threshold
        self.ks_threshold = ks_threshold
        self.psi_bins = psi_bins
        self.psi_thresholds = psi_thresholds
        self.min_samples = min_samples

        self.results = {
            "mean_drift": None,
            "median_drift": None,
            "variance_drift": None,
            "quantile_drift": None,
            "ks_test": None,
            "psi": None,
            "alerts": [],
            "overall_drift": False
        }

    # ---------------- Utility ----------------
    @staticmethod
    def _relative_change(curr, base):
        if base == 0:
            return None
        return abs(curr - base) / abs(base)

    @staticmethod
    def _compute_psi(base, current, bins=10):
        # create breakpoints from baseline
        breakpoints = np.percentile(base, np.linspace(0, 100, bins + 1))
        breakpoints[0] = -np.inf
        breakpoints[-1] = np.inf

        base_counts = np.histogram(base, bins=breakpoints)[0] / len(base)
        curr_counts = np.histogram(current, bins=breakpoints)[0] / len(current)

        # avoid division by zero
        base_counts = np.clip(base_counts, 1e-6, None)
        curr_counts = np.clip(curr_counts, 1e-6, None)

        psi = np.sum((base_counts - curr_counts) * np.log(base_counts / curr_counts))
        return psi

    # ---------------- Regression Metrics ----------------
    def monitor_regression(self):
        base = self.baseline["pred"].dropna()
        curr = self.current["pred"].dropna()

        if len(base) < self.min_samples or len(curr) < self.min_samples:
            return

        results = {}

        # Mean
        mean_base = base.mean()
        mean_curr = curr.mean()
        rc_mean = self._relative_change(mean_curr, mean_base)
        if rc_mean is not None and rc_mean > self.mean_threshold:
            results["mean_drift"] = rc_mean

        # Median
        median_base = base.median()
        median_curr = curr.median()
        rc_median = self._relative_change(median_curr, median_base)
        if rc_median is not None and rc_median > self.median_threshold:
            results["median_drift"] = rc_median

        # Variance
        var_base = base.var(ddof=0)
        var_curr = curr.var(ddof=0)
        rc_var = self._relative_change(var_curr, var_base)
        if rc_var is not None and rc_var > self.variance_threshold:
            results["variance_drift"] = rc_var

        # Quantiles
        quantile_changes = {}
        for q in self.quantiles:
            q_base = base.quantile(q)
            q_curr = curr.quantile(q)
            rc_q = self._relative_change(q_curr, q_base)
            if rc_q is not None and rc_q > self.variance_threshold:  # same as variance threshold
                quantile_changes[q] = rc_q
        if quantile_changes:
            results["quantile_drift"] = quantile_changes

        # KS test
        ks_stat, p_val = ks_2samp(base, curr)
        results["ks_test"] = {"ks_stat": ks_stat, "p_value": p_val, "drift": ks_stat > self.ks_threshold}

        # PSI
        psi_val = self._compute_psi(base, curr, bins=self.psi_bins)
        if psi_val < self.psi_thresholds[0]:
            severity = "low"
        elif psi_val < self.psi_thresholds[1]:
            severity = "medium"
        else:
            severity = "high"
        results["psi"] = {"psi": psi_val, "severity": severity}

        self.results.update(results)

        # Alerting: if multiple metrics drift
        signal_count = sum([
            "mean_drift" in results,
            "median_drift" in results,
            "variance_drift" in results,
            results["psi"]["severity"] == "high",
            results["ks_test"]["drift"]
        ])
        if signal_count >= 2:
            self.results["alerts"].append("regression_output_drift")

    # ---------------- Classification Metrics ----------------
    def monitor_classification(self):
        base = self.baseline["pred"].dropna()
        curr = self.current["pred"].dropna()

        if len(base) < self.min_samples or len(curr) < self.min_samples:
            return

        results = {}

        # Class distribution
        base_counts = base.value_counts(normalize=True)
        curr_counts = curr.value_counts(normalize=True)

        # Drift per class
        class_drift = {}
        for cls in base_counts.index:
            b = base_counts.get(cls, 0)
            c = curr_counts.get(cls, 0)
            rc = self._relative_change(c, b)
            if rc is not None and rc > self.mean_threshold:  # same threshold for class ratio
                class_drift[cls] = rc
        if class_drift:
            results["class_ratio_drift"] = class_drift

        # KS test on label integers (if multi-class)
        # Convert categories to integers if not already
        try:
            base_int = base.astype(int)
            curr_int = curr.astype(int)
            ks_stat, p_val = ks_2samp(base_int, curr_int)
            results["ks_test"] = {"ks_stat": ks_stat, "p_value": p_val, "drift": ks_stat > self.ks_threshold}
        except:
            results["ks_test"] = {"ks_stat": None, "p_value": None, "drift": False}

        # PSI on class probabilities
        psi_val = self._compute_psi(base.map(base_counts).values, curr.map(curr_counts).values, bins=self.psi_bins)
        if psi_val < self.psi_thresholds[0]:
            severity = "low"
        elif psi_val < self.psi_thresholds[1]:
            severity = "medium"
        else:
            severity = "high"
        results["psi"] = {"psi": psi_val, "severity": severity}

        self.results.update(results)

        # Alerting: multiple signals
        signal_count = sum([
            "class_ratio_drift" in results,
            results["psi"]["severity"] == "high",
            results["ks_test"]["drift"]
        ])
        if signal_count >= 2:
            self.results["alerts"].append("classification_output_drift")

    # ---------------- Run ----------------
    def monitor(self):
        """Run monitoring without storing results."""
        if self.task_type == "regression":
            self.monitor_regression()
        elif self.task_type == "classification":
            self.monitor_classification()
        else:
            raise ValueError("task_type must be 'regression' or 'classification'")
        
        # Set overall_drift flag
        self.results["overall_drift"] = len(self.results["alerts"]) > 0
        return self.results
    
    async def run(self):
        """Execute full prediction drift monitoring with LLM interpretation and database storage."""
        # Run monitoring
        self.monitor()
        
        # Store results with LLM interpretation
        await self.store_results()
        
        return self.results
    
    async def store_results(self):
        """Store prediction drift results in database with LLM interpretation."""
        # Generate LLM interpretation
        llm_msg = None
        try:
            llm_msg = await interpret_prediction_drift(
                project_id=self.project_id,
                drift_results=self.results,
                task_type=self.task_type,
                baseline_window=self.baseline_window,
                current_window=self.current_window
            )
            print(f"✓ LLM interpretation generated for project {self.project_id}")
        except Exception as e:
            print(f"Warning: Failed to generate LLM interpretation: {str(e)}")
            llm_msg = None
        
        # Store in database
        async with AsyncSessionLocal() as db:
            try:
                drift_record = models.PredictionDrift(
                    project_id=self.project_id,
                    batch_number=self.batch_no or 0,
                    baseline_window=self.baseline_window,
                    current_window=self.current_window,
                    drift_results={
                        "mean_drift": self.results.get("mean_drift"),
                        "median_drift": self.results.get("median_drift"),
                        "variance_drift": self.results.get("variance_drift"),
                        "quantile_drift": self.results.get("quantile_drift")
                    },
                    ks_test=self.results.get("ks_test", {}),
                    psi=self.results.get("psi", {}),
                    alerts=self.results.get("alerts", []),
                    overall_drift=self.results.get("overall_drift", False),
                    llm_interpretation=llm_msg
                )
                db.add(drift_record)
                await db.commit()
                print(f"✓ Prediction Drift stored for project {self.project_id}, batch {self.batch_no}")
                
            except Exception as e:
                await db.rollback()
                print(f"Error storing prediction drift: {str(e)}")
