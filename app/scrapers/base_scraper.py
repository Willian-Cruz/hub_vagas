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
    """Contrato dos scrapers com Template Method de coleta.

    O Template Method `coletar()` é implementado pelo pai e cuida de:
      - loop de páginas (1..MAX_PAGES)
      - detecção de página repetida (links já vistos)
      - detecção de página sem resultados (markers do robots/portal)
      - tratamento de exceção por página e na coleta global
      - rate-limiting (intervalo com jitter entre páginas)
      - montagem do ScrapeResult final

    Os filhos implementam apenas:
      - `_buscar_pagina(numero_pagina)` → conteúdo HTML/bytes da página
      - `_parsear_cards(conteudo)` → (vagas, cards_invalidos, total_cards)
    """

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

    # ── Deep scraping (item 3) ─────────────────────────────────────────────
    # Número máximo de vagas para as quais buscar a página de detalhe.
    # 0 = desativado. Subclasses definem > 0 quando suportam deep scraping.
    MAX_DETAIL_PAGES = 0

    # ── Linhagem de dados (M09) ─────────────────────────────────────────────
    # Versão do scraper, gravada em raw.job_observations.scraper_version para
    # permitir rastrear qualquer registro da Gold de volta à execução original.
    SCRAPER_VERSION = "1.0.0"

    # ── Template Method ───────────────────────────────────────────────────
    @classmethod
    def coletar(cls) -> ScrapeResult:
        """Template Method: orquestra a coleta paginada da fonte.

        Não deve ser sobrescrito pelos filhos. Eles implementam
        `_buscar_pagina()` e `_parsear_cards()`.
        """
        todas_vagas: list[JobSchema] = []
        paginas_processadas = 0
        cards_invalidos_total = 0
        erro_coleta: str | None = None
        links_vistos: set[str] = set()

        for numero_pagina in range(1, cls.MAX_PAGES + 1):
            # Rate-limiting entre páginas
            cls._aguardar_intervalo_com_jitter()
            cls._log(f"Coletando página {numero_pagina}/{cls.MAX_PAGES}")

            # ── 1. Buscar conteúdo da página (filho implementa) ─────────
            try:
                conteudo = cls._buscar_pagina(numero_pagina)
            except Exception as exc:
                msg = f"Página {numero_pagina}: {type(exc).__name__}: {exc}"
                cls._log(f"Falha na requisição: {msg}")
                erro_coleta = msg
                break

            paginas_processadas += 1

            # ── 2. Parse dos cards (filho implementa) ───────────────────
            try:
                vagas_pagina, invalidos, cards_encontrados = cls._parsear_cards(
                    conteudo
                )
            except Exception as exc:
                msg = f"Página {numero_pagina}: erro ao parsear: {type(exc).__name__}: {exc}"
                cls._log(f"Falha ao parsear: {msg}")
                erro_coleta = msg
                break

            cards_invalidos_total += invalidos

            # ── 3. Detecção de fim de paginação ─────────────────────────
            if not vagas_pagina:
                if links_vistos and cards_encontrados == 0:
                    # Fim normal: já vimos links, esta página está vazia
                    break
                if not links_vistos and cls._pagina_sem_resultados(conteudo):
                    # Estado vazio explícito do portal
                    break
                if cards_encontrados == 0:
                    erro_coleta = (
                        f"A página não contém o seletor esperado."
                    )
                elif invalidos:
                    erro_coleta = (
                        f"{invalidos} card(s) sem título ou link válido."
                    )
                break

            # ── 4. Detecção de links repetidos (página já vista) ────────
            vagas_novas = [
                vaga for vaga in vagas_pagina if vaga.link not in links_vistos
            ]
            if not vagas_novas:
                cls._log(
                    f"Página {numero_pagina} repetiu links anteriores; "
                    "encerrando paginação."
                )
                break

            links_vistos.update(vaga.link for vaga in vagas_novas)
            todas_vagas.extend(vagas_novas)
            cls._log(
                f"Página {numero_pagina}: {len(vagas_novas)} vaga(s) de "
                f"{len(vagas_pagina)} card(s)"
            )

        # ── 4b. Deep scraping: buscar páginas de detalhe (opcional) ─────
        if cls.MAX_DETAIL_PAGES > 0:
            cls._log(
                f"Deep scraping: buscando detalhe de até {cls.MAX_DETAIL_PAGES} "
                f"vaga(s) de {len(todas_vagas)} coletada(s)"
            )
            for vaga in todas_vagas[: cls.MAX_DETAIL_PAGES]:
                if not vaga.detail_url:
                    continue
                cls._aguardar_intervalo_com_jitter()
                try:
                    detail_html = cls.fetch_detail_page(vaga.detail_url)
                    if detail_html:
                        vaga = cls._merge_detail_into_vaga(vaga, detail_html)
                        # Substitui a vaga na lista (JobSchema é imutável -> pydantic cria nova)
                        idx = todas_vagas.index(vaga)
                        todas_vagas[idx] = vaga
                except Exception as exc:
                    cls._log(f"Falha ao buscar detalhe de {vaga.detail_url}: {exc}")

        # ── 5. Montagem do ScrapeResult final ───────────────────────────
        status = cls._determinar_status(
            erro_coleta=erro_coleta,
            cards_invalidos=cards_invalidos_total,
            todas_vagas=todas_vagas,
            links_vistos=links_vistos,
        )

        # ── Linhagem (M09): definir scraper_version em todas as vagas ───
        todas_vagas = [
            vaga.model_copy(update={"scraper_version": cls.SCRAPER_VERSION})
            for vaga in todas_vagas
        ]

        cls._log(
            f"Resultado: {status.value}; {len(todas_vagas)} vaga(s); "
            f"{paginas_processadas} página(s) processada(s)"
        )

        return ScrapeResult(
            source=cls.SOURCE,
            status=status,
            jobs=todas_vagas,
            pages_processed=paginas_processadas,
            error=erro_coleta,
            discarded=0,  # filtro de relevância aplicado centralmente
        )

    @classmethod
    def _determinar_status(
        cls,
        *,
        erro_coleta: str | None,
        cards_invalidos: int,
        todas_vagas: list[JobSchema],
        links_vistos: set[str],
    ) -> ScrapeStatus:
        """Determina o status final com base no resultado da coleta."""
        if erro_coleta:
            return (
                ScrapeStatus.PARTIAL
                if links_vistos
                else ScrapeStatus.FAILED
            )
        if cards_invalidos:
            return ScrapeStatus.PARTIAL
        if todas_vagas:
            return ScrapeStatus.SUCCESS
        return ScrapeStatus.EMPTY

    # ── Contrato que os filhos devem implementar ──────────────────────────

    @classmethod
    @abstractmethod
    def _buscar_pagina(cls, numero_pagina: int):
        """Busca o conteúdo bruto (HTML/bytes) da página número `numero_pagina`."""

    @classmethod
    @abstractmethod
    def _parsear_cards(
        cls, conteudo
    ) -> tuple[list[JobSchema], int, int]:
        """Extrai (vagas válidas, cards inválidos, total de cards) do conteúdo."""

    # ── Deep scraping (item 3) ─────────────────────────────────────────────
    # Opcional: subclasses que conseguem navegar até a página de detalhe
    # sobrescrevem este método. Retorna o HTML da página de detalhe ou None
    # quando o portal não suporta / não foi implementado.
    @classmethod
    def fetch_detail_page(cls, detail_url: str) -> str | None:
        """Busca o HTML da página de detalhe de uma vaga.

        Implementação padrão não faz nada (retorna None). Subclasses que
        suportam deep scraping (ex.: Vagas.com) sobrescrevem este método
        usando Playwright ou requests conforme o portal exigir.
        """
        return None

    @classmethod
    def _merge_detail_into_vaga(
        cls, vaga: JobSchema, detail_html: str | None
    ) -> JobSchema:
        """Mescla dados extraídos da página de detalhe na vaga.

        Implementação padrão não altera nada. Subclasses sobrescrevem para
        preencher descricao completa, salario detalhado, etc.
        """
        return vaga

    # ── Utilitários compartilhados ────────────────────────────────────────

    @classmethod
    def _aguardar_intervalo_com_jitter(cls) -> None:
        """Espera um intervalo aleatório desde o último request entre requests."""
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

    # ── Retry com backoff exponencial + jitter (item #8) ────────────────
    @classmethod
    def coletar_com_retry(cls) -> ScrapeResult:
        """Executa `coletar()` com retry exponencial + jitter para erros de rede."""
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
                if resultado.status != ScrapeStatus.FAILED or not resultado.error:
                    return resultado
                ultimo_resultado = resultado
            except (TypeError,) as exc:
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
