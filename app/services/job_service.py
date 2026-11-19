from app.database.connection import SessionLocal
from app.database.job_model import Job


class JobService:

    @staticmethod
    def salvar(vaga):
        
        session = SessionLocal()

        try:
            job=Job(
                titulo=vaga.titulo,
                empresa=vaga.empresa,
                localizacao=vaga.localizacao,
                descricao=vaga.descricao,
                link=vaga.link,
                origem=vaga.origem,
            )        
            session.add(job)

            session.commit()
        finally:
            session.close()
