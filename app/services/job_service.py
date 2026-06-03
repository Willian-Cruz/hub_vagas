from database.connection import Sessionlocal
from database.job_model import Job

class JobService:

    @staticmethod
    def salvar(vaga):
        
        session = Sessionlocal()

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
