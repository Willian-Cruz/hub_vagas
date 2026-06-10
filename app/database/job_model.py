from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from database.models import base
from database.job_tech_model import job_technologies

class Job(base):

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    titulo = Column(String)
    empresa = Column(String)
    senioridade = Column(String)
    localizacao = Column(String)
    descricao = Column(Text)
    salario = Column(String)
    link = Column(String, unique=True, nullable=False)
    origem = Column(String)

    technologies = relationship(
        "Technology", 
        secondary=job_technologies, 
        back_populates="jobs"
    )