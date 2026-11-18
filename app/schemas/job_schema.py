from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


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

    # URL da página de detalhe da vaga (quando o scraper consegue navegar até ela).
    # Usado para deep scraping: captura descrição completa e salário do card detalhado.
    detail_url: Optional[str] = None

    # Identificação e metadados que o card do portal já traz
    id_externo: Optional[str] = None        # ID da vaga no portal (estável entre coletas)
    data_publicacao: Optional[datetime] = None
    modalidade: Optional[str] = None        # Presencial / Híbrido / Remoto
    experiencia: Optional[str] = None       # ex.: "Sem experiência", "Entre 1 e 3 anos"
    escolaridade: Optional[str] = None      # ex.: "Ensino Superior"
    qtd_posicoes: Optional[int] = None      # ex.: "Pleno - 2 vagas" -> 2

    # Filtro de relevância: True quando o título casa com termos_relevancia.csv.
    # Quando False, motivo_relevancia registra por que foi descartada.
    is_relevant: bool = True
    motivo_relevancia: Optional[str] = None

    # O fragmento é mantido para Bronze, mas não integra o contrato normalizado.
    raw_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)

    # Linhagem de dados (M09): versão do scraper que coletou esta vaga,
    # gravada em raw.job_observations.scraper_version para permitir rastrear
    # qualquer registro da Gold de volta à execução original.
    scraper_version: Optional[str] = "1.0.0"

    @field_validator("titulo")
    @classmethod
    def _titulo_nao_vazio(cls, v: str) -> str:
        """Rejeita título vazio ou apenas espaços em branco."""
        if v is None or not v.strip():
            raise ValueError("titulo não pode ser vazio ou conter apenas espaços")
        return v

    @field_validator("link")
    @classmethod
    def _link_nao_vazio(cls, v: str) -> str:
        """Rejeita link vazio ou apenas espaços em branco."""
        if v is None or not v.strip():
            raise ValueError("link não pode ser vazio ou conter apenas espaços")
        return v

    @field_validator("origem")
    @classmethod
    def _origem_nao_vazio(cls, v: str) -> str:
        """Rejeita origem vazia ou apenas espaços em branco."""
        if v is None or not v.strip():
            raise ValueError("origem não pode ser vazia ou conter apenas espaços")
        return v
