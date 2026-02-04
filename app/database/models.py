from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    TIMESTAMP,
    func,
    Float,
    JSON,
    Index,
    Boolean
)
from sqlalchemy.orm import relationship
import uuid
from app.database.connection import Base

class Company(Base):
    __tablename__ = "company"

    company_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=True, unique=True)
    session_token = Column(String(255), index=True)

    projects = relationship(
        "Project",
        back_populates="company",
        cascade="all, delete-orphan"
    )


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("company.company_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_name = Column(String(255), nullable=False,unique=True)
    project_description = Column(Text, nullable = True)
    access_token = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    company = relationship("Company", back_populates="projects")

    # NEW relationships
    feature_inputs = relationship(
        "FeatureInput",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    prediction_outputs = relationship(
        "PredictionOutput",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    data_stats = relationship(
        "ProjectDataStats",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

    quality_checks = relationship(
        "DataQualityCheck",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    validation_params = relationship(
        "DataValidationParameters",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

    validations = relationship(
        "DataValidation",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    prediction_metrics = relationship(
        "PredictionMetrics",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    prediction_drifts = relationship(
        "PredictionDrift",
        back_populates="project",
        cascade="all, delete-orphan"
    )


class FeatureInput(Base):
    __tablename__ = "feature_input"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    row_id = Column(Integer, nullable=False, index=True)
    features = Column(JSON, nullable=False)  # store all features as JSON
    stage = Column(String(50), nullable=False, default="model_input", index=True)  # monitoring stage
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="feature_inputs")

    # Optional index for faster lookups by project and stage
    __table_args__ = (
        Index("idx_feature_input_project", "project_id"),
        Index("idx_feature_project_stage", "project_id", "stage"),
    )


class PredictionOutput(Base):
    __tablename__ = "prediction_output"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    row_id = Column(Integer, nullable=False, index=True)
    prediction = Column(JSON, nullable=True)  # store predictions as JSON
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="prediction_outputs")

    # Optional index for faster lookups by project and stage
    __table_args__ = (
        Index("idx_prediction_output_project", "project_id"),
    )

# ---------- PROJECT CONFIG ----------

class ProjectConfig(Base):
    __tablename__ = "project_config"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    baseline_batch_size = Column(Integer, nullable=False, default=1000)
    monitor_batch_size = Column(Integer, nullable=False, default=500)
    monitoring_stage = Column(String(50), nullable=False, default="model_input")  # single stage per project

    project = relationship("Project", back_populates="config")


# Add back_populates in Project
Project.config = relationship(
    "ProjectConfig",
    back_populates="project",
    uselist=False,  # one config per project
    cascade="all, delete-orphan"
)


# ---------- MONITOR BATCH/STATS INFO ----------

class ProjectDataStats(Base):
    __tablename__ = "project_data_stats"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Specific ranges for the LATEST ingestion event
    latest_feature_start_row = Column(Integer, nullable=True)
    latest_feature_end_row = Column(Integer, nullable=True)
    latest_prediction_start_row = Column(Integer, nullable=True)
    latest_prediction_end_row = Column(Integer, nullable=True)
    
    # Overall counters
    total_batches = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    last_ingestion_at = Column(
        TIMESTAMP, 
        server_default=func.now(), 
        onupdate=func.now()
    )

    project = relationship("Project", back_populates="data_stats")

# ---------- DATA QUALITY CHECKS ----------

class DataQualityCheck(Base):
    __tablename__ = "data_quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Batch information
    batch_number = Column(Integer, nullable=False)
    check_timestamp = Column(TIMESTAMP, server_default=func.now())
    
    # Row range checked
    feature_start_row = Column(Integer, nullable=True)
    feature_end_row = Column(Integer, nullable=True)
    total_rows_checked = Column(Integer, default=0)
    
    # Missing value results (stored as JSON)
    missing_values_summary = Column(JSON, nullable=True)  # {column: {count: X, percentage: Y}}
    
    # Duplicate row results (stored as JSON)
    duplicate_percentage = Column(Float, default = 0.0)
    total_duplicate_rows = Column(Integer, default=0)
    
    # Overall statistics
    total_columns_checked = Column(Integer, default=0)
    columns_with_missing = Column(Integer, default=0)
    
    # Status
    check_status = Column(String(50), default="completed")  # completed, failed, pending
    error_message = Column(Text, nullable=True)
    
    project = relationship("Project", back_populates="quality_checks")

    __table_args__ = (
        Index("idx_quality_project_batch", "project_id", "batch_number"),
    )

# ---------- DATA VALIDATION ----------

class DataValidationParameters(Base):
    """Stores the expected schema (rules) for a project's data"""
    __tablename__ = "data_validation_parameters"
    __table_args__ = {"keep_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    
    len_columns = Column(Integer, nullable=False)
    columns_type = Column(JSON, nullable=False)  # {"col1": "float64", "col2": "object"}
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    project = relationship("Project", back_populates="validation_params")


class DataValidation(Base):
    """Stores the results of validating a batch against the parameters"""
    __tablename__ = "data_validation"
    __table_args__ = {"keep_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    batch_number = Column(Integer, nullable=False)
    
    # Specific check results
    len_columns_status = Column(Boolean, nullable=False)
    columns_type_status = Column(Boolean, nullable=False)
    
    # Overall status
    validation_status = Column(Boolean, nullable=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    project = relationship("Project", back_populates="validations")


# ---------- BASELINE INFO ----------

class BaselineInfo(Base):
    __tablename__ = "baseline_info"

    baseline_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    baseline_start_row_feature_input = Column(Integer, nullable=False)  # start of baseline window
    baseline_end_row_feature_input = Column(Integer, nullable=False,default = 1)    # end of baseline window

    baseline_start_row_prediction_output = Column(Integer, nullable=False)
    baseline_end_row_prediction_output = Column(Integer, nullable=False)

    temp_baseline_batch_size = Column(Integer, nullable = False)

    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="baselines")

    __table_args__ = (
        Index("idx_baseline_project_created", "project_id", "created_at"),
    )


# Add back_populates in Project
Project.baselines = relationship(
    "BaselineInfo",
    back_populates="project",
    cascade="all, delete-orphan"
)

class MonitorInfo(Base):
    __tablename__ = "monitor_info"

    monitor_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    monitor_start_row_feature_input = Column(Integer, nullable=False)  # start of monitoring window
    monitor_end_row_feature_input = Column(Integer, nullable=False)  # end of monitoring window


# ---------- DATA DRIFT ----------


class DataDriftConfig(Base):
    __tablename__ = 'data_drift_config'

    config_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    mean_threshold = Column(Float, nullable=False, default=0.1)
    median_threshold = Column(Float, nullable=False, default=0.1)
    variance_threshold = Column(Float, nullable=False, default=0.2)
    quantile_threshold = Column(Float, nullable=False, default=0.2)

    ks_pvalue_threshold = Column(Float, nullable=False, default=0.05)

    psi_threshold = Column(JSON, nullable=False, default=[0.1, 0.25])
    psi_bins = Column(Integer, nullable=False, default=10)
    min_samples = Column(Integer, nullable=False, default=50)

    alert_threshold = Column(Integer, nullable=False, default=2)  # Number of signals to trigger alert

    model_based_drift_threshold = Column(Float, nullable=False, default=0.50)

    created_at = Column(TIMESTAMP, server_default=func.now())


class DataDrift(Base):
    __tablename__ = "data_drift"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # batch_no = Column(Integer, nullable=True) # Optional batch number

    baseline_window = Column(String, nullable=False)  # e.g., "rows 1–1000"
    current_window = Column(String, nullable=False)   # e.g., "rows 1001–1500"
    
    # Source timestamps for traceability
    baseline_source_timestamp = Column(TIMESTAMP, nullable=True) 
    current_source_timestamp = Column(TIMESTAMP, nullable=True)

    feature_stats = Column(JSON, nullable=False)     # Baseline + current feature stats (JSONB in PG, JSON in Base)
    drift_tests = Column(JSON, nullable=False)       # All statistical test results
    alerts = Column(JSON, nullable=False)            # List of features with drift
    overall_drift = Column(Boolean, nullable=False)
    drift_score = Column(Float, nullable=True)
    
    # LLM-generated interpretation and recommendations
    llm_interpretation = Column(Text, nullable=True) # LLM analysis of drift results

    created_at = Column(TIMESTAMP, server_default=func.now())
    
    project = relationship("Project", back_populates="drift_snapshots")
    
    __table_args__ = (
        Index("idx_drift_snapshot_project_time", "project_id", "created_at"),
    )

# Add relation to Project
Project.drift_snapshots = relationship("DataDrift", back_populates="project", cascade="all, delete-orphan")


class ModelBasedDrift(Base):
    __tablename__ = 'model_based_drift'

    drift_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    drift_score = Column(Float, nullable=False)  # Model accuracy (higher = more drift)
    alert_triggered = Column(Boolean, default=False)
    alert_threshold = Column(Float, nullable=False)  # Threshold used for this test
    
    baseline_samples = Column(Integer, nullable=False)
    current_samples = Column(Integer, nullable=False)
    
    # Source timestamps
    baseline_source_timestamp = Column(TIMESTAMP, nullable=True) 
    current_source_timestamp = Column(TIMESTAMP, nullable=True)
    
    model_type = Column(String(50), default="RandomForest")
    test_accuracy = Column(Float, nullable=False)
    
    test_happened_at_time = Column(TIMESTAMP, server_default=func.now())
    
    project = relationship("Project", back_populates="model_drifts")

    __table_args__ = (
        Index("idx_model_drift_project_time", "project_id", "test_happened_at_time"),
    )

# Add relation to Project
Project.model_drifts = relationship(
    "ModelBasedDrift", 
    back_populates="project",
    cascade="all, delete-orphan"
)


# ---------- PREDICTION MONITORING ----------

class PredictionMetrics(Base):
    __tablename__ = "prediction_metrics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    batch_number = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    
    # Combined metrics storage
    metrics = Column(JSON, nullable=False)  # stores {accuracy: x, precision: y, ...}
    
    metadata_info = Column(JSON, nullable=True)  # user-provided metadata
    
    project = relationship("Project", back_populates="prediction_metrics")

    __table_args__ = (
        Index("idx_pred_metrics_project_batch", "project_id", "batch_number"),
    )


class PredictionDrift(Base):
    __tablename__ = "prediction_drift"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    batch_number = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    # Window info
    baseline_window = Column(String, nullable=False)
    current_window = Column(String, nullable=False)

    # Drift results
    drift_results = Column(JSON, nullable=False)  # includes mean, median, variance, quantile drifts
    ks_test = Column(JSON, nullable=False)
    psi = Column(JSON, nullable=False)
    alerts = Column(JSON, nullable=False)
    overall_drift = Column(Boolean, nullable=False, default=False)
    
    # LLM-generated interpretation and recommendations
    llm_interpretation = Column(Text, nullable=True) # LLM analysis of prediction drift results
    
    project = relationship("Project", back_populates="prediction_drifts")

    __table_args__ = (
        Index("idx_pred_drift_project_batch", "project_id", "batch_number"),
    )