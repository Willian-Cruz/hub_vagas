from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from bs4 import BeautifulSoup

from schemas.job_schema import JobSchema
from services.relevance_service import RelevanceService


class ScrapeStatus(str, Enum):
    SUCCESS = "success"
    EMPTY = "empty"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(slots=True)
class ScrapeResult:
    """Resultado de uma coleta, incluindo falhas que antes viravam lista vazia."""

    source: str
    status: ScrapeStatus
    jobs: list[JobSchema] = field(default_factory=list)
    pages_processed: int = 0
    error: str | None = None
    discarded: int = 0  # vagas fora do tema, descartadas pelo filtro de relevância


class BaseScraper(ABC):
    """Contrato dos scrapers e resultado padronizado de cada fonte."""

    MAX_PAGES = 10
    SOURCE = "unknown"
    LOG_DESCARTADAS = 10  # quantos títulos descartados aparecem no log
    EMPTY_STATE_MARKERS = (
        "nenhuma vaga",
        "não encontramos vagas",
        "nao encontramos vagas",
        "nenhum resultado",
        "nenhuma oportunidade",
        "no jobs found",
        "no results found",
    )

    @classmethod
    @abstractmethod
    def coletar(cls) -> ScrapeResult:
        """Coleta a fonte e informa estado, vagas, páginas e eventual erro."""

    @classmethod
    def _pagina_sem_resultados(cls, html: str | bytes) -> bool:
        texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).casefold()
        return any(marcador in texto for marcador in cls.EMPTY_STATE_MARKERS)

    @classmethod
    def _aplicar_filtro_relevancia(
        cls, vagas: list[JobSchema]
    ) -> tuple[list[JobSchema], list[JobSchema]]:
        """Separa vagas do tema das que só casaram na busca e registra as descartadas."""
        relevantes, descartadas = RelevanceService.separar(vagas)
        if descartadas:
            amostra = "; ".join(v.titulo for v in descartadas[: cls.LOG_DESCARTADAS])
            resto = len(descartadas) - cls.LOG_DESCARTADAS
            sufixo = f" (+{resto})" if resto > 0 else ""
            cls._log(f"{len(descartadas)} vaga(s) fora do tema descartada(s): {amostra}{sufixo}")
        return relevantes, descartadas

    @classmethod
    def _log(cls, msg: str) -> None:
        print(f"[{cls.__name__}] {msg}")
