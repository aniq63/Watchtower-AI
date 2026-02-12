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

# =============================================================================
# CORE MODELS
# =============================================================================

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
    project_name = Column(String(255), nullable=False, unique=True)
    project_description = Column(Text, nullable=True)
    access_token = Column(String(255), nullable=True, unique=True, index=True)
    total_batches = Column(Integer, default=0, nullable=False)
    project_type = Column(
        String(50), 
        nullable=False, 
        default="feature_monitoring"
    )  # Options: 'feature_monitoring', 'llm_monitoring', 'prediction_monitoring'
    created_at = Column(TIMESTAMP, server_default=func.now())

    company = relationship("Company", back_populates="projects")

    # FEATURE MONITORING Relationships
    feature_inputs = relationship(
        "FeatureInput",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    feature_config = relationship(
        "FeatureConfig",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    feature_drifts = relationship(
        "FeatureDrift", 
        back_populates="project", 
        cascade="all, delete-orphan"
    )
    feature_stats = relationship(
        "FeatureStats",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    feature_quality_checks = relationship(
        "FeatureQualityCheck",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    feature_validation_params = relationship(
        "FeatureValidationParams",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    feature_validations = relationship(
        "FeatureValidation",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    model_drifts = relationship(
        "ModelBasedDrift", 
        back_populates="project",
        cascade="all, delete-orphan"
    )
    feature_baselines = relationship(
        "FeatureBaseline",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    feature_monitor_info = relationship(
        "FeatureMonitorInfo",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # PREDICTION MONITORING Relationships
    prediction_outputs = relationship(
        "PredictionOutput",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    prediction_config = relationship(
        "PredictionConfig",
        back_populates="project",
        uselist=False,
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

    # LLM MONITORING Relationships
    llm_config = relationship(
        "LLMConfig",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    llm_monitors = relationship(
        "LLMMonitor",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    llm_baselines = relationship(
        "LLMBaseline",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    llm_monitor_infos = relationship(
        "LLMMonitorInfo",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    llm_drifts = relationship(
        "LLMDrift",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    # New Config Relationships
    prediction_evaluation_config = relationship(
        "PredictionEvaluationConfig",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    llm_drift_config = relationship(
        "LLMDriftConfig",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )
    llm_evaluation_config = relationship(
        "LLMEvaluationConfig",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan"
    )

# =============================================================================
# FEATURE MONITORING SDK
# =============================================================================

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
    features = Column(JSON, nullable=False)
    stage = Column(String(50), nullable=False, default="model_input", index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="feature_inputs")

    __table_args__ = (
        Index("idx_feature_input_project_id", "project_id"),
        Index("idx_feature_input_project_stage", "project_id", "stage"),
    )

class FeatureConfig(Base):
    __tablename__ = "feature_config"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    baseline_batch_size = Column(Integer, nullable=False, default=1000)
    monitor_batch_size = Column(Integer, nullable=False, default=500)
    monitoring_stage = Column(String(50), nullable=False, default="model_input")

    project = relationship("Project", back_populates="feature_config")

class FeatureDriftConfig(Base):
    __tablename__ = 'feature_drift_config'

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
    ks_pvalue_threshold = Column(Float, nullable=False, default=0.05)
    psi_threshold = Column(JSON, nullable=False, default=[0.1, 0.25])
    psi_bins = Column(Integer, nullable=False, default=10)
    min_samples = Column(Integer, nullable=False, default=50)
    alert_threshold = Column(Integer, nullable=False, default=2)
    model_based_drift_threshold = Column(Float, nullable=False, default=0.50)
    created_at = Column(TIMESTAMP, server_default=func.now())

class FeatureDrift(Base):
    __tablename__ = "feature_drift"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    baseline_window = Column(String, nullable=False)
    current_window = Column(String, nullable=False)
    baseline_source_timestamp = Column(TIMESTAMP, nullable=True) 
    current_source_timestamp = Column(TIMESTAMP, nullable=True)
    feature_stats = Column(JSON, nullable=False)
    drift_tests = Column(JSON, nullable=False)
    alerts = Column(JSON, nullable=False)
    overall_drift = Column(Boolean, nullable=False)
    drift_score = Column(Float, nullable=True)
    llm_interpretation = Column(Text, nullable=True)
    test_happened_at_time = Column(TIMESTAMP, server_default=func.now())
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    project = relationship("Project", back_populates="feature_drifts")
    
    __table_args__ = (
        Index("idx_feature_drift_project_time", "project_id", "test_happened_at_time"),
    )

class ModelBasedDrift(Base):
    __tablename__ = 'model_based_drift'

    drift_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    drift_score = Column(Float, nullable=False)
    alert_triggered = Column(Boolean, default=False)
    alert_threshold = Column(Float, nullable=False)
    baseline_samples = Column(Integer, nullable=False)
    current_samples = Column(Integer, nullable=False)
    baseline_source_timestamp = Column(TIMESTAMP, nullable=True) 
    current_source_timestamp = Column(TIMESTAMP, nullable=True)
    model_type = Column(String(50), default="RandomForest")
    test_accuracy = Column(Float, nullable=False)
    test_happened_at_time = Column(TIMESTAMP, server_default=func.now())
    
    project = relationship("Project", back_populates="model_drifts")

    __table_args__ = (
        Index("idx_model_based_drift_project_time", "project_id", "test_happened_at_time"),
    )

class FeatureStats(Base):
    __tablename__ = "feature_stats"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    latest_feature_start_row = Column(Integer, nullable=True)
    latest_feature_end_row = Column(Integer, nullable=True)
    latest_prediction_start_row = Column(Integer, nullable=True)
    latest_prediction_end_row = Column(Integer, nullable=True)
    total_batches = Column(Integer, default=0, nullable=False)
    last_ingestion_at = Column(
        TIMESTAMP, 
        server_default=func.now(), 
        onupdate=func.now()
    )

    project = relationship("Project", back_populates="feature_stats")

class FeatureQualityCheck(Base):
    __tablename__ = "feature_quality_check"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    batch_number = Column(Integer, nullable=False)
    check_timestamp = Column(TIMESTAMP, server_default=func.now())
    feature_start_row = Column(Integer, nullable=True)
    feature_end_row = Column(Integer, nullable=True)
    total_rows_checked = Column(Integer, default=0)
    missing_values_summary = Column(JSON, nullable=True)
    duplicate_percentage = Column(Float, default=0.0)
    total_duplicate_rows = Column(Integer, default=0)
    total_columns_checked = Column(Integer, default=0)
    columns_with_missing = Column(Integer, default=0)
    check_status = Column(String(50), default="completed")
    error_message = Column(Text, nullable=True)
    
    project = relationship("Project", back_populates="feature_quality_checks")

    __table_args__ = (
        Index("idx_feature_quality_project_batch", "project_id", "batch_number"),
    )

class FeatureValidationParams(Base):
    __tablename__ = "feature_validation_params"
    __table_args__ = {"keep_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    len_columns = Column(Integer, nullable=False)
    columns_type = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    project = relationship("Project", back_populates="feature_validation_params")

class FeatureValidation(Base):
    __tablename__ = "feature_validation"
    __table_args__ = {"keep_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    batch_number = Column(Integer, nullable=False)
    len_columns_status = Column(Boolean, nullable=False)
    columns_type_status = Column(Boolean, nullable=False)
    validation_status = Column(Boolean, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    project = relationship("Project", back_populates="feature_validations")

class FeatureBaseline(Base):
    __tablename__ = "feature_baseline"

    baseline_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    baseline_start_row_feature_input = Column(Integer, nullable=False)
    baseline_end_row_feature_input = Column(Integer, nullable=False, default=1)
    baseline_start_row_prediction_output = Column(Integer, nullable=False)
    baseline_end_row_prediction_output = Column(Integer, nullable=False, default=1)
    temp_baseline_batch_size = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="feature_baselines")

    __table_args__ = (
        Index("idx_feature_baseline_project_created", "project_id", "created_at"),
    )

class FeatureMonitorInfo(Base):
    __tablename__ = "feature_monitor_info"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    monitor_start_row_feature_input = Column(Integer, nullable=False)
    monitor_end_row_feature_input = Column(Integer, nullable=False)

    project = relationship("Project", back_populates="feature_monitor_info")

# =============================================================================
# PREDICTION MONITORING SDK
# =============================================================================

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
    prediction = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="prediction_outputs")

    __table_args__ = (
        Index("idx_prediction_output_project_id", "project_id"),
    )

class PredictionConfig(Base):
    __tablename__ = "prediction_config"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    baseline_batch_size = Column(Integer, nullable=False, default=1000)
    monitor_batch_size = Column(Integer, nullable=False, default=500)

    project = relationship("Project", back_populates="prediction_config")

class PredictionDriftConfig(Base):
    __tablename__ = 'prediction_drift_config'

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
    ks_pvalue_threshold = Column(Float, nullable=False, default=0.05)
    psi_threshold = Column(JSON, nullable=False, default=[0.1, 0.25])
    psi_bins = Column(Integer, nullable=False, default=10)
    min_samples = Column(Integer, nullable=False, default=50)
    alert_threshold = Column(Integer, nullable=False, default=2)
    model_based_drift_threshold = Column(Float, nullable=False, default=0.50)
    created_at = Column(TIMESTAMP, server_default=func.now())

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
    metrics = Column(JSON, nullable=False)
    metadata_info = Column(JSON, nullable=True)
    
    project = relationship("Project", back_populates="prediction_metrics")

    __table_args__ = (
        Index("idx_prediction_metrics_project_batch", "project_id", "batch_number"),
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
    baseline_window = Column(String, nullable=False)
    current_window = Column(String, nullable=False)
    drift_results = Column(JSON, nullable=False)
    ks_test = Column(JSON, nullable=False)
    psi = Column(JSON, nullable=False)
    alerts = Column(JSON, nullable=False)
    overall_drift = Column(Boolean, nullable=False, default=False)
    llm_interpretation = Column(Text, nullable=True)
    
    project = relationship("Project", back_populates="prediction_drifts")

    __table_args__ = (
        Index("idx_prediction_drift_project_batch", "project_id", "batch_number"),
    )

# =============================================================================
# LLM MONITORING SDK
# =============================================================================

class LLMConfig(Base):
    __tablename__ = "llm_config"

    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        primary_key=True
    )
    baseline_batch_size = Column(Integer, nullable=False, default=500)
    monitor_batch_size = Column(Integer, nullable=False, default=250)
    toxicity_threshold = Column(Float, nullable=False, default=0.5)
    token_drift_threshold = Column(Float, nullable=False, default=0.15)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="llm_config")

class LLMMonitor(Base):
    __tablename__ = "llm_monitor"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    row_id = Column(Integer, nullable=False, index=True)
    input_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    response_token_length = Column(Integer, nullable=False)
    detoxify = Column(JSON, nullable=False)
    is_toxic = Column(Boolean, nullable=False, default=False)
    llm_judge_metrics = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="llm_monitors")

    __table_args__ = (
        Index("idx_llm_monitor_project_id", "project_id"),
        Index("idx_llm_monitor_project_row_id", "project_id", "row_id"),
        Index("idx_llm_monitor_project_created", "project_id", "created_at"),
    )

class LLMBaseline(Base):
    __tablename__ = "llm_baseline"

    baseline_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    baseline_start_row = Column(Integer, nullable=False)
    baseline_end_row = Column(Integer, nullable=False)
    avg_response_token_length = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="llm_baselines")

    __table_args__ = (
        Index("idx_llm_baseline_project_id", "project_id"),
    )

class LLMMonitorInfo(Base):
    __tablename__ = "llm_monitor_info"

    monitor_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    monitor_start_row = Column(Integer, nullable=False)
    monitor_end_row = Column(Integer, nullable=False)
    current_avg_token_length = Column(Float, nullable=True)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="llm_monitor_infos")

    __table_args__ = (
        Index("idx_llm_monitor_info_project_id", "project_id"),
    )

class LLMDrift(Base):
    __tablename__ = "llm_drift"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    baseline_window = Column(String, nullable=False)
    monitor_window = Column(String, nullable=False)
    baseline_avg_tokens = Column(Float, nullable=False)
    monitor_avg_tokens = Column(Float, nullable=False)
    token_length_change = Column(Float, nullable=False)
    has_drift = Column(Boolean, nullable=False, default=False)
    drift_interpretation = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="llm_drifts")

    __table_args__ = (
        Index("idx_llm_drift_project_id", "project_id"),
        Index("idx_llm_drift_project_created", "project_id", "created_at"),
    )

class PredictionEvaluationConfig(Base):
    __tablename__ = "prediction_evaluation_config"

    config_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    metric_thresholds = Column(JSON, nullable=False, default={})
    min_samples = Column(Integer, nullable=False, default=50)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="prediction_evaluation_config")

class LLMDriftConfig(Base):
    __tablename__ = "llm_drift_config"

    config_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_drift_threshold = Column(Float, nullable=False, default=0.15)
    embedding_drift_threshold = Column(Float, nullable=False, default=0.2)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="llm_drift_config")

class LLMEvaluationConfig(Base):
    __tablename__ = "llm_evaluation_config"

    config_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    toxicity_threshold = Column(Float, nullable=False, default=0.5)
    hallucination_threshold = Column(Float, nullable=False, default=0.5)
    relevance_threshold = Column(Float, nullable=False, default=0.7)
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="llm_evaluation_config")