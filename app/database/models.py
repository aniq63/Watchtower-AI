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
    Index
)
from sqlalchemy.orm import relationship
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

# ---------- NEW TABLES ----------

class FeatureInput(Base):
    __tablename__ = "feature_input"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    features = Column(JSON, nullable=False)  # store all features as JSON
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="feature_inputs")

    # Optional index for faster lookups by project
    __table_args__ = (
        Index("idx_feature_input_project", "project_id"),
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
    prediction = Column(JSON, nullable=True)  # store predictions as JSON
    created_at = Column(TIMESTAMP, server_default=func.now())

    project = relationship("Project", back_populates="prediction_outputs")

    # Optional index for faster lookups by project
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

    project = relationship("Project", back_populates="config")


# Add back_populates in Project
Project.config = relationship(
    "ProjectConfig",
    back_populates="project",
    uselist=False,  # one config per project
    cascade="all, delete-orphan"
)


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
    start_row = Column(Integer, nullable=False)  # start of baseline window
    end_row = Column(Integer, nullable=False)    # end of baseline window
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
