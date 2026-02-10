# ============ DATA INGESTION DEFAULTS ============
DEFAULT_BASELINE_BATCH_SIZE = 1000  # Rows to use for baseline
DEFAULT_MONITOR_BATCH_SIZE = 500    # Rows to use for monitoring window
DEFAULT_INGESTION_STAGE = "model_input"

# ============ DRIFT DETECTION THRESHOLDS ============
# Statistical drift detection thresholds (relative change)
DRIFT_MEAN_THRESHOLD = 0.1          # 10% relative change
DRIFT_MEDIAN_THRESHOLD = 0.1        # 10% relative change
DRIFT_VARIANCE_THRESHOLD = 0.2      # 20% relative change

# KS Test threshold
DRIFT_KS_PVALUE_THRESHOLD = 0.05    # p-value threshold for statistical significance

# PSI (Population Stability Index) thresholds
DRIFT_PSI_LOW_THRESHOLD = 0.1       # Low drift
DRIFT_PSI_MEDIUM_THRESHOLD = 0.25   # Medium drift
DRIFT_PSI_BINS = 10                 # Number of bins for PSI calculation

# Minimum samples for statistical tests
DRIFT_MIN_SAMPLES = 50              # Minimum samples needed for valid drift detection
DRIFT_ALERT_THRESHOLD = 2           # Number of signals needed to trigger alert

# Model-based drift detection
MODEL_BASED_DRIFT_THRESHOLD = 0.50  # Accuracy threshold for model-based drift
MODEL_RF_N_ESTIMATORS = 200         # RandomForest estimators count
MODEL_RF_RANDOM_STATE = 42          # RandomForest random seed
MODEL_RF_TEST_SIZE = 0.2            # Test set proportion for model evaluation

# ============ DATA QUALITY DEFAULTS ============
QUALITY_CHECK_DUPLICATE_METHOD = "first"  # How to handle duplicates: 'first', 'last', False

# ============ TIME & EXPIRATION ============
SESSION_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days

# ============ API & TIMEOUTS ============
API_TIMEOUT_SECONDS = 30
SDK_POST_TIMEOUT_SECONDS = 30

# ============ LLM CONFIGURATION ============
LLM_MODEL_NAME = "openai/gpt-oss-20b"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 1024

# ============ DATABASE ============
DB_ECHO_DEBUG = False               # Echo SQL queries in debug mode
DB_STATEMENT_CACHE_SIZE = 0         # For Supabase compatibility
