from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobSchema(BaseModel):
    """Vaga coletada por um scraper.

    Campo sem informação é ``None``, nunca o texto "Não informado": o texto
    vira categoria falsa no Power BI e impede distinguir "o portal não informa"
    de "o seletor falhou".
    """

    titulo: str
    empresa: Optional[str] = None
    senioridade: Optional[str] = None
    localizacao: Optional[str] = None
    descricao: Optional[str] = None
    salario: Optional[str] = None
    link: str
    origem: str

    # Identificação e metadados que o card do portal já traz
    id_externo: Optional[str] = None        # ID da vaga no portal (estável entre coletas)
    data_publicacao: Optional[datetime] = None
    modalidade: Optional[str] = None        # Presencial / Híbrido / Remoto
    experiencia: Optional[str] = None       # ex.: "Sem experiência", "Entre 1 e 3 anos"
    escolaridade: Optional[str] = None      # ex.: "Ensino Superior"
    qtd_posicoes: Optional[int] = None      # ex.: "Pleno - 2 vagas" -> 2
