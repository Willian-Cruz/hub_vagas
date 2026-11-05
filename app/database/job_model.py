from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.models import base
from database.job_tech_model import job_technologies

class Job(base):

    __tablename__ = "jobs"
    __table_args__ = (
        # O mesmo ID de vaga no mesmo portal não pode entrar duas vezes.
        # Em bancos antigos o índice equivalente vem da migration 004.
        UniqueConstraint("origem", "id_externo", name="uq_jobs_origem_id_externo"),
    )

    id = Column(Integer, primary_key=True)
    titulo = Column(String)
    empresa = Column(String)
    senioridade = Column(String)
    localizacao = Column(String)
    descricao = Column(Text)
    salario = Column(String)
    link = Column(String, unique=True, nullable=False)
    origem = Column(String)
    data_coleta = Column(DateTime, server_default=func.now(), nullable=False)

    # Campos que o card do portal já traz (migration 004)
    id_externo = Column(String)
    data_publicacao = Column(DateTime)
    modalidade = Column(String)
    experiencia = Column(String)
    escolaridade = Column(String)
    qtd_posicoes = Column(Integer)
    # origem|título|empresa|local normalizados: pega a mesma vaga republicada
    # com outro ID. Fica NULL quando falta empresa ou local.
    chave_conteudo = Column(String, index=True)

    technologies = relationship(
        "Technology",
        secondary=job_technologies,
        back_populates="jobs"
    )
