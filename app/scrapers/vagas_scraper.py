import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from constants.selectors import (
    VAGAS_COMPANY,
    VAGAS_DESCRIPTION,
    VAGAS_JOB_CARD,
    VAGAS_LOCATION,
    VAGAS_SENIORITY,
    VAGAS_TITLE,
)
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper, ScrapeResult, ScrapeStatus


class VagasScraper(BaseScraper):
    """Scraper para vagas.com.br, que carrega resultados com infinite scroll."""

    SOURCE = "Vagas.com"
    URL = (
        "https://www.vagas.com.br/vagas-de-engenheiro-de-dados"
        "?ordenar_por=mais_recentes"
    )
    MAX_PAGES = 20  # máximo de scrolls após o carregamento da página inicial
    RESULTS_WAIT_MS = 10_000
    NEW_RESULTS_WAIT_MS = 6_000
    MAX_NO_CHANGE = 3
    NAVIGATION_TIMEOUT_MS = 40_000

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    @classmethod
    def coletar(cls) -> ScrapeResult:
        paginas_processadas = 0
        browser = None

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(user_agent=cls.USER_AGENT)
                    cls._log(f"Acessando {cls.URL}")
                    response = page.goto(
                        cls.URL,
                        timeout=cls.NAVIGATION_TIMEOUT_MS,
                        wait_until="domcontentloaded",
                    )
                    paginas_processadas = 1

                    status_http = getattr(response, "status", None)
                    if status_http is not None and status_http >= 400:
                        return cls._resultado_falha(
                            f"Portal respondeu HTTP {status_http}.", paginas_processadas
                        )

                    try:
                        page.wait_for_selector(
                            VAGAS_JOB_CARD,
                            state="attached",
                            timeout=cls.RESULTS_WAIT_MS,
                        )
                    except PlaywrightTimeout:
                        html = page.content()
                        jobs, invalidos, cards = cls._parsear_detalhado(html)
                        if jobs:
                            return ScrapeResult(
                                source=cls.SOURCE,
                                status=ScrapeStatus.PARTIAL,
                                jobs=jobs,
                                pages_processed=paginas_processadas,
                                error="Timeout aguardando o seletor; cards apareceram no HTML.",
                            )
                        if cards == 0 and cls._pagina_sem_resultados(html):
                            return ScrapeResult(
                                source=cls.SOURCE,
                                status=ScrapeStatus.EMPTY,
                                pages_processed=paginas_processadas,
                            )
                        detalhe = (
                            f"{invalidos} card(s) sem título ou link válido."
                            if invalidos
                            else f"Nenhum card '{VAGAS_JOB_CARD}' apareceu após o carregamento."
                        )
                        return cls._resultado_falha(detalhe, paginas_processadas)

                    sem_novidade = 0
                    for scroll_num in range(cls.MAX_PAGES):
                        vagas_antes = page.locator(VAGAS_JOB_CARD).count()
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                        try:
                            page.wait_for_function(
                                "count => "
                                "document.querySelectorAll('li.vaga').length > count",
                                arg=vagas_antes,
                                timeout=cls.NEW_RESULTS_WAIT_MS,
                            )
                            sem_novidade = 0
                        except PlaywrightTimeout:
                            sem_novidade += 1

                        vagas_depois = page.locator(VAGAS_JOB_CARD).count()
                        cls._log(
                            f"Scroll {scroll_num + 1}/{cls.MAX_PAGES}: "
                            f"{vagas_depois} card(s) carregados"
                        )

                        if sem_novidade >= cls.MAX_NO_CHANGE:
                            break
                        if vagas_depois > vagas_antes:
                            time.sleep(0.5)

                    html = page.content()
                    jobs, invalidos, cards = cls._parsear_detalhado(html)

                    if not jobs:
                        if cards == 0 and cls._pagina_sem_resultados(html):
                            return ScrapeResult(
                                source=cls.SOURCE,
                                status=ScrapeStatus.EMPTY,
                                pages_processed=paginas_processadas,
                            )
                        detalhe = (
                            f"{invalidos} card(s) sem título ou link válido."
                            if invalidos
                            else f"HTML não contém cards válidos '{VAGAS_JOB_CARD}'."
                        )
                        return cls._resultado_falha(detalhe, paginas_processadas)

                    status = (
                        ScrapeStatus.PARTIAL if invalidos else ScrapeStatus.SUCCESS
                    )
                    erro = (
                        f"{invalidos} card(s) ignorado(s) por dados incompletos."
                        if invalidos
                        else None
                    )
                    cls._log(f"Resultado: {status.value}; {len(jobs)} vaga(s)")
                    return ScrapeResult(
                        source=cls.SOURCE,
                        status=status,
                        jobs=jobs,
                        pages_processed=paginas_processadas,
                        error=erro,
                    )
                finally:
                    browser.close()
        except Exception as exc:
            return cls._resultado_falha(
                f"{type(exc).__name__}: {exc}", paginas_processadas
            )

        return cls._resultado_falha("A navegação terminou sem resultado.", paginas_processadas)

    @classmethod
    def _resultado_falha(cls, erro: str, paginas_processadas: int) -> ScrapeResult:
        cls._log(f"Falha na coleta: {erro}")
        return ScrapeResult(
            source=cls.SOURCE,
            status=ScrapeStatus.FAILED,
            pages_processed=paginas_processadas,
            error=erro,
        )

    @classmethod
    def _parsear(cls, html: str) -> list[JobSchema]:
        """Extrai vagas do HTML; separado para testes sem navegador/rede."""
        return cls._parsear_detalhado(html)[0]

    @classmethod
    def _parsear_detalhado(cls, html: str) -> tuple[list[JobSchema], int, int]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(VAGAS_JOB_CARD)
        vagas: list[JobSchema] = []
        cards_invalidos = 0
        links_vistos = set()

        for card in cards:
            titulo_el = card.select_one(VAGAS_TITLE)
            titulo = titulo_el.get_text(" ", strip=True) if titulo_el else ""
            link_el = card.select_one(VAGAS_TITLE)
            href = (link_el.get("href") or "").strip() if link_el else ""

            if not titulo or not href:
                cards_invalidos += 1
                continue

            empresa_el = card.select_one(VAGAS_COMPANY)
            empresa = (
                empresa_el.get_text(" ", strip=True)
                if empresa_el
                else "Não informado"
            )

            senioridade_el = card.select_one(VAGAS_SENIORITY)
            senioridade = (
                senioridade_el.get_text(" ", strip=True)
                if senioridade_el
                else "Não informado"
            )

            localizacao_el = card.select_one(VAGAS_LOCATION)
            localizacao = (
                localizacao_el.get_text(" ", strip=True)
                if localizacao_el
                else "Não informado"
            )
            localizacao = localizacao.split("A empresa aceita")[0].strip()

            descricao_el = card.select_one(VAGAS_DESCRIPTION)
            descricao = (
                descricao_el.get_text(" ", strip=True)
                if descricao_el
                else "Não informado"
            )

            link = urljoin("https://www.vagas.com.br/", href)
            if link in links_vistos:
                continue
            links_vistos.add(link)

            vagas.append(
                JobSchema(
                    titulo=titulo,
                    empresa=empresa or "Não informado",
                    senioridade=senioridade or "Não informado",
                    localizacao=localizacao or "Não informado",
                    descricao=descricao or "Não informado",
                    link=link,
                    origem=cls.SOURCE,
                    raw_payload={"html_fragment": str(card)},
                )
            )

        return vagas, cards_invalidos, len(cards)
