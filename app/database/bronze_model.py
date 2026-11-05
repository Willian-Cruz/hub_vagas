"""Modelos de persistência da camada Bronze no PostgreSQL."""
from sqlalchemy import (
    Column,
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from database.models import base


class ScrapeRun(base):
    """Resultado de uma execução de um scraper dentro de um pipeline."""

    __tablename__ = "scrape_runs"
    __table_args__ = (
        {"schema": "bronze"},
    )

    run_id = Column(UUID(as_uuid=True), primary_key=True)
    source = Column(String(80), primary_key=True)
    status = Column(String(20), nullable=False)
    pages_processed = Column(Integer, nullable=False, server_default="0")
    jobs_found = Column(Integer, nullable=False, server_default="0")
    error = Column(Text)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobObservation(base):
    """Snapshot imutável dos campos entregues pelo scraper para uma vaga."""

    __tablename__ = "job_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "source"],
            ["bronze.scrape_runs.run_id", "bronze.scrape_runs.source"],
            name="fk_bronze_observation_run",
        ),
        UniqueConstraint(
            "run_id",
            "source",
            "source_job_id",
            name="uq_bronze_observation_run_source_job",
        ),
        Index(
            "ix_bronze_observations_source_collected_at",
            "source",
            "collected_at",
        ),
        Index("ix_bronze_observations_source_job_id", "source", "source_job_id"),
        {"schema": "bronze"},
    )

    id = Column(BigInteger, primary_key=True)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    source = Column(String(80), nullable=False)
    source_job_id = Column(String(1000), nullable=False)
    collected_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload_hash = Column(String(64), nullable=False)
    raw_payload = Column(JSONB, nullable=False)
