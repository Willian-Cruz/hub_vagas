from sqlalchemy import Table, Column, Integer, ForeignKey
from database.models import base

job_technologies = Table(
    "job_technologies",
    base.metadata,
    Column("job_id", Integer, ForeignKey("jobs.id")),
    Column("technology_id", Integer, ForeignKey("technologies.id")),
    )