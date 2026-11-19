from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.job_tech_model import job_technologies
from app.database.models import base


class Technology(base):

    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True, nullable=False)

    jobs = relationship(
        "Job", 
        secondary= job_technologies, 
        back_populates="technologies"
    )
