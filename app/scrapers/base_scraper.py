from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import random
import time

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

    # ── Compliance (item #12) ─────────────────────────────────────────────
    USER_AGENT = (
        "hub-vagas-bot/1.0 "
        "(+https://github.com/Willian-Cruz/hub_vagas; contato via issues)"
    )
    # Intervalo aleatório entre requests (segundos) para não saturar o portal.
    MIN_INTER_REQUEST_DELAY = 2.0
    MAX_INTER_REQUEST_DELAY = 5.0
    _ultimo_request_ts = 0.0  # timestamp do último request (compartilhado pela classe)

    # ── Retry com backoff exponencial + jitter (item #8) ────────────────
    MAX_RETRIES = 3          # número de tentativas após a primeira falha
    RETRY_BACKOFF_BASE = 2   # segundos base para backoff exponencial

    @classmethod
    def _aguardar_intervalo_com_jitter(cls) -> None:
        """Espera um intervalo aleatório desde o último request entre requests.

        Implementa compliance de rate-limiting: não dispara requests em
        sucessão rápida no mesmo portal.
        """
        agora = time.time()
        espera = random.uniform(
            cls.MIN_INTER_REQUEST_DELAY, cls.MAX_INTER_REQUEST_DELAY
        )
        decorrido = agora - cls._ultimo_request_ts
        if decorrido < espera:
            time.sleep(espera - decorrido)
        cls._ultimo_request_ts = time.time()

    @classmethod
    def _headers(cls) -> dict:
        """Headers HTTP com User-Agent identificável (compliance)."""
        return {"User-Agent": cls.USER_AGENT}

    @classmethod
    @abstractmethod
    def coletar(cls) -> ScrapeResult:
        """Coleta a fonte e informa estado, vagas, páginas e eventual erro."""

    @classmethod
    def coletar_com_retry(cls) -> ScrapeResult:
        """Executa `coletar()` com retry exponencial + jitter para erros de rede.

        Erros transitórios (timeout, TLS, conexão recusada) são retentados até
        MAX_RETRIES vezes com backoff exponencial e jitter, antes de devolver
        o último ScrapeResult (sucesso ou falha).
        """
        tentativa = 0
        ultimo_resultado = None

        while tentativa <= cls.MAX_RETRIES:
            try:
                resultado = cls.coletar()
                if not isinstance(resultado, ScrapeResult):
                    raise TypeError(
                        f"{cls.__name__}.coletar() deve retornar ScrapeResult, "
                        f"recebido: {type(resultado).__name__}"
                    )
                # Se a coleta teve sucesso ou retornou vazio/partial sem exceção,
                # não há motivo para retry por erro de rede.
                if resultado.status != ScrapeStatus.FAILED or not resultado.error:
                    return resultado
                # FAILED com erro: pode ser erro de rede, tenta novamente
                ultimo_resultado = resultado
            except (TypeError,) as exc:
                # Erro de contrato (não é ScrapeResult) não é retryável: falha imediatamente
                ultimo_resultado = ScrapeResult(
                    source=cls.SOURCE,
                    status=ScrapeStatus.FAILED,
                    error=str(exc),
                )
                break
            except Exception as exc:
                ultimo_resultado = ScrapeResult(
                    source=cls.SOURCE,
                    status=ScrapeStatus.FAILED,
                    error=f"{type(exc).__name__}: {exc}",
                )

            tentativa += 1
            if tentativa <= cls.MAX_RETRIES:
                backoff = cls.RETRY_BACKOFF_BASE ** tentativa
                jitter = random.uniform(0, backoff * 0.3)
                espera = backoff + jitter
                cls._log(
                    f"Tentativa {tentativa}/{cls.MAX_RETRIES} falhou; "
                    f"retry em {espera:.1f}s (backoff+jitter)"
                )
                time.sleep(espera)

        # Todas as tentativas esgotadas: devolve o último resultado (falha)
        if ultimo_resultado is not None:
            cls._log(
                f"Todas as {cls.MAX_RETRIES + 1} tentativas esgotadas para {cls.SOURCE}"
            )
            return ultimo_resultado

        return ScrapeResult(
            source=cls.SOURCE,
            status=ScrapeStatus.FAILED,
            error="coleta falhou sem retornar resultado",
        )

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
