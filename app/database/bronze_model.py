"""Modelos de persistência da camada Bronze no PostgreSQL."""
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
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
