from database.models import Technology
from database.connection import SessionLocal


class TechnologyRepository:

    @staticmethod
    def obter_ou_criar(nome):

        session = SessionLocal()

        tecnologia = session.query(Technology).filter(Technology.nome == nome).first()

        if tecnologia:

            session.close()
            return tecnologia

        tecnologia = Technology(nome=nome)

        session.add(tecnologia)

        session.commit()

        session.refresh(tecnologia)

        session.close()

        return tecnologia
