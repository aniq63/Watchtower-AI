import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sqlalchemy import select, func
from app.database import models
from app.database.connection import AsyncSessionLocal
from app.services.feature_monitoring.drift_llm_interpreter import interpret_data_drift
from app.constants import (
    DRIFT_MEAN_THRESHOLD,
    DRIFT_MEDIAN_THRESHOLD,
    DRIFT_VARIANCE_THRESHOLD,
    DRIFT_KS_PVALUE_THRESHOLD,
    DRIFT_PSI_LOW_THRESHOLD,
    DRIFT_PSI_MEDIUM_THRESHOLD,
    DRIFT_PSI_BINS,
    DRIFT_MIN_SAMPLES,
    DRIFT_ALERT_THRESHOLD
)


class InputDataDriftMonitor:
    def __init__(
        self,
        project_id,
        baseline_data,
        current_data,
        batch_no=None,
        baseline_window_str="unknown",
        current_window_str="unknown",
        baseline_timestamp=None,
        current_timestamp=None,
        # Thresholds (can be None, will load defaults)
        mean_threshold=None,
        median_threshold=None,
        variance_threshold=None,
        ks_pvalue_threshold=None,
        psi_thresholds=None,
        psi_bins=None,
        min_samples=None,
        alert_threshold=None
    ):
        """
        Initialize the data drift monitor with Snapshot architecture.
        """
        self.project_id = project_id
        
        # Convert numpy array to DataFrame if needed
        if isinstance(baseline_data, np.ndarray):
            baseline_data = pd.DataFrame(baseline_data)
        if isinstance(current_data, np.ndarray):
            current_data = pd.DataFrame(current_data)

        self.baseline_data = baseline_data
        self.current_data = current_data
        
        # Snapshot Metadata
        self.batch_no = batch_no
        self.baseline_window = baseline_window_str
        self.current_window = current_window_str
        self.baseline_timestamp = baseline_timestamp
        self.current_timestamp = current_timestamp

        self.numeric_cols = baseline_data.select_dtypes(include="number").columns

        # Thresholds
        self.mean_threshold = mean_threshold
        self.median_threshold = median_threshold
        self.variance_threshold = variance_threshold
        self.ks_pvalue_threshold = ks_pvalue_threshold
        self.psi_thresholds = psi_thresholds
        self.psi_bins = psi_bins
        self.min_samples = min_samples
        self.alert_threshold = alert_threshold
        
        # Unified Result Structure
        self.snapshot_data = {
            "feature_stats": {},
            "drift_tests": {},
            "alerts": [],
            "overall_drift": False,
            "drift_score": 0.0
        }

    async def load_config(self):
        """Load drift detection configuration from database."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(models.FeatureDriftConfig).where(
                    models.FeatureDriftConfig.project_id == self.project_id
                )
            )
            config = result.scalars().first()
            
            if not config:
                # Use defaults from constants if no config found
                print(f"No drift config found for project {self.project_id}, using defaults")
                if self.mean_threshold is None: self.mean_threshold = DRIFT_MEAN_THRESHOLD
                if self.median_threshold is None: self.median_threshold = DRIFT_MEDIAN_THRESHOLD
                if self.variance_threshold is None: self.variance_threshold = DRIFT_VARIANCE_THRESHOLD
                if self.ks_pvalue_threshold is None: self.ks_pvalue_threshold = DRIFT_KS_PVALUE_THRESHOLD
                if self.psi_thresholds is None: self.psi_thresholds = (DRIFT_PSI_LOW_THRESHOLD, DRIFT_PSI_MEDIUM_THRESHOLD)
                if self.psi_bins is None: self.psi_bins = DRIFT_PSI_BINS
                if self.min_samples is None: self.min_samples = DRIFT_MIN_SAMPLES
                if self.alert_threshold is None: self.alert_threshold = DRIFT_ALERT_THRESHOLD
                return
            
            # Load from config if not provided in init
            if self.mean_threshold is None: self.mean_threshold = config.mean_threshold
            if self.median_threshold is None: self.median_threshold = config.median_threshold
            if self.variance_threshold is None: self.variance_threshold = config.variance_threshold
            if self.ks_pvalue_threshold is None: self.ks_pvalue_threshold = config.ks_pvalue_threshold
            if self.psi_thresholds is None: self.psi_thresholds = tuple(config.psi_threshold) if isinstance(config.psi_threshold, list) else (0.1, 0.25)
            if self.psi_bins is None: self.psi_bins = config.psi_bins
            if self.min_samples is None: self.min_samples = config.min_samples
            if self.alert_threshold is None: self.alert_threshold = config.alert_threshold

    # ---------- Calculation Helpers ----------

    def _calculate_stats(self, series: pd.Series) -> dict:
        """Compute basic stats for a numeric series."""
        if len(series) == 0:
            return None
        
        # Handle NaN/None for robust stats
        clean_series = series.dropna()
        if len(clean_series) == 0:
            return None

        return {
            "mean": float(clean_series.mean()),
            "median": float(clean_series.median()),
            "std": float(clean_series.std(ddof=1)) if len(clean_series) > 1 else 0.0,

            "quantiles": {
                "0.25": float(clean_series.quantile(0.25)),
                "0.5": float(clean_series.quantile(0.5)),
                "0.75": float(clean_series.quantile(0.75))
            },
            "missing_count": int(series.isna().sum()),
            "total_count": int(len(series))
        }

    def _relative_change(self, curr, base):
        if base == 0 or base is None or curr is None:
            return None
        return abs(curr - base) / abs(base)

    def _compute_psi(self, base, curr):
        """Calculate PSI between two distributions."""
        try:
            base = base.dropna()
            curr = curr.dropna()
            
            if len(base) == 0 or len(curr) == 0:
                return None, "unknown"

            breakpoints = np.percentile(base, np.linspace(0, 100, self.psi_bins + 1))
            breakpoints[0] = -np.inf
            breakpoints[-1] = np.inf

            base_counts = np.histogram(base, bins=breakpoints)[0] / len(base)
            curr_counts = np.histogram(curr, bins=breakpoints)[0] / len(curr)

            # Avoid zero division
            base_counts = np.clip(base_counts, 1e-6, None)
            curr_counts = np.clip(curr_counts, 1e-6, None)

            psi = np.sum((base_counts - curr_counts) * np.log(base_counts / curr_counts))
            
            severity = "low"
            if psi >= self.psi_thresholds[1]: severity = "high"
            elif psi >= self.psi_thresholds[0]: severity = "medium"
            
            return float(psi), severity
        except Exception:
            return None, "error"

    def _run_tests_for_column(self, col: str, base_series: pd.Series, curr_series: pd.Series) -> dict:
        """Run all drift tests for a specific column."""
        tests = {}
        alerts_count = 0
        
        base_clean = base_series.dropna()
        curr_clean = curr_series.dropna()
        
        if len(base_clean) < self.min_samples or len(curr_clean) < self.min_samples:
            return None, 0

        # 1. Mean Drift
        b_mean = base_clean.mean()
        c_mean = curr_clean.mean()
        mean_rc = self._relative_change(c_mean, b_mean)
        if mean_rc is not None:
            tests["mean_shift"] = {
                "value": float(mean_rc),
                "threshold": self.mean_threshold,
                "drift_detected": bool(mean_rc > self.mean_threshold)
            }
            if mean_rc > self.mean_threshold: alerts_count += 1
            
        # 2. Median Drift
        b_med = base_clean.median()
        c_med = curr_clean.median()
        med_rc = self._relative_change(c_med, b_med)
        if med_rc is not None:
            tests["median_shift"] = {
                "value": float(med_rc),
                "threshold": self.median_threshold,
                "drift_detected": bool(med_rc > self.median_threshold)
            }
            if med_rc > self.median_threshold: alerts_count += 1

        # 3. Variance Drift
        b_var = base_clean.var()
        c_var = curr_clean.var()
        var_rc = self._relative_change(c_var, b_var)
        if var_rc is not None:
            tests["variance_shift"] = {
                "value": float(var_rc),
                "threshold": self.variance_threshold,
                "drift_detected": bool(var_rc > self.variance_threshold)
            }
            if var_rc > self.variance_threshold: alerts_count += 1
            
        # 3. KS Test
        try:
            stat, p_value = ks_2samp(base_clean, curr_clean)
            is_drift = p_value < self.ks_pvalue_threshold
            tests["ks_test"] = {
                "statistic": float(stat),
                "p_value": float(p_value),
                "threshold": self.ks_pvalue_threshold,
                "drift_detected": bool(is_drift)
            }
            if is_drift: alerts_count += 1
        except:
            pass
            
        # 4. PSI
        psi_val, severity = self._compute_psi(base_clean, curr_clean)
        if psi_val is not None:
            tests["psi"] = {
                "value": float(psi_val),
                "severity": severity,
                "thresholds": self.psi_thresholds
            }
            if severity == "high": alerts_count += 1
            
        return tests, alerts_count

    # ---------- Main Execution ----------

    async def run(self):
        """Execute the full drift monitoring workflow."""
        await self.load_config()
        
        alerted_features = []
        total_drift_score = 0.0
        
        for col in self.numeric_cols:
            base_series = self.baseline_data[col]
            curr_series = self.current_data[col]
            
            # A. Compute Stats for both baseline and current
            baseline_stats = self._calculate_stats(base_series)
            current_stats = self._calculate_stats(curr_series)
            
            self.snapshot_data["feature_stats"][col] = {
                "baseline": baseline_stats,
                "current": current_stats
            }
            
            # B. Run Tests
            tests, alert_signals = self._run_tests_for_column(col, base_series, curr_series)
            if tests:
                self.snapshot_data["drift_tests"][col] = tests
                
                # Check for Alert
                if alert_signals >= self.alert_threshold:
                    alerted_features.append(col)
                    self.snapshot_data["overall_drift"] = True

        self.snapshot_data["alerts"] = alerted_features
        # Simple drift score: % of alerted features
        if len(self.numeric_cols) > 0:
            self.snapshot_data["drift_score"] = len(alerted_features) / len(self.numeric_cols)
        
        await self.store_results()
        
        return self.snapshot_data

    async def store_results(self):
        """Store the snapshot in the database with LLM interpretation."""
        # Generate LLM interpretation
        llm_msg = None
        try:
            llm_msg = await interpret_data_drift(
                project_id=self.project_id,
                drift_snapshot=self.snapshot_data,
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
                snapshot = models.FeatureDrift(
                    project_id=self.project_id,
                    baseline_window=self.baseline_window,
                    current_window=self.current_window,
                    baseline_source_timestamp=self.baseline_timestamp,
                    current_source_timestamp=self.current_timestamp,
                    feature_stats=self.snapshot_data["feature_stats"],
                    drift_tests=self.snapshot_data["drift_tests"],
                    alerts=self.snapshot_data["alerts"],
                    overall_drift=self.snapshot_data["overall_drift"],
                    drift_score=self.snapshot_data["drift_score"],
                    llm_interpretation=llm_msg,
                    test_happened_at_time=func.now()
                )
                db.add(snapshot)
                await db.commit()
                print(f"✓ Drift Snapshot stored for project {self.project_id}")
                
            except Exception as e:
                await db.rollback()
                print(f"Error storing drift snapshot: {str(e)}")

