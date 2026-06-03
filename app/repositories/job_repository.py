from database.connection import Sessionlocal
from database.job_model import Job
from database.tech_model import Technology
from services.tech_service import TechnologyService


class JobRepository:

    @staticmethod
    def salvar(vaga):

        session = Sessionlocal()

        try:

            vaga_existente = session.query(Job).filter(Job.link == vaga.link).first()

            if vaga_existente:

                print(f"Vaga já existe: " f"{vaga.titulo}")

                return

            nova_vaga = Job(
                titulo=vaga.titulo,
                empresa=vaga.empresa,
                senioridade=vaga.senioridade,
                localizacao=vaga.localizacao,
                descricao=vaga.descricao,
                link=vaga.link,
                origem=vaga.origem,
            )

            session.add(nova_vaga)
            
            tecnologias = TechnologyService.extrair(vaga.descricao)

            for tech_nome in tecnologias:

                tecnologia = (
                    session.query(Technology)
                    .filter(Technology.nome == tech_nome)
                    .first()
                )

                if not tecnologia:

                    tecnologia = Technology(nome=tech_nome)

                    session.add(tecnologia)

                    session.flush()

                nova_vaga.technologies.append(tecnologia)

            session.add(nova_vaga)

            session.commit()

            print(f"Salva: {vaga.titulo}")

        except Exception as e:

            session.rollback()

            print(f"Erro ao salvar vaga: {e}")

        finally:

            session.close()