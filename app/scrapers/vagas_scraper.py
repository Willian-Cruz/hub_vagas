import re
import time
from datetime import date
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from constants.selectors import (
    VAGAS_COMPANY,
    VAGAS_DATE,
    VAGAS_DESCRIPTION,
    VAGAS_JOB_CARD,
    VAGAS_LOCATION,
    VAGAS_LOCATION_NOISE,
    VAGAS_POSITIONS,
    VAGAS_SENIORITY,
    VAGAS_TITLE,
)
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper, ScrapeResult, ScrapeStatus
from utils.date_utils import parse_data_vagas
from utils.text_utils import normalizar_espacos, valor_ou_none


class VagasScraper(BaseScraper):
    """Scraper para vagas.com.br, que carrega resultados com infinite scroll."""

    SOURCE = "Vagas.com"
    BASE_URL = "https://www.vagas.com.br/"
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

    _ID_NO_LINK = re.compile(r"/vagas/v(\d+)")

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
                            relevantes, descartadas = cls._aplicar_filtro_relevancia(jobs)
                            return ScrapeResult(
                                source=cls.SOURCE,
                                status=ScrapeStatus.PARTIAL,
                                jobs=relevantes,
                                pages_processed=paginas_processadas,
                                error="Timeout aguardando o seletor; cards apareceram no HTML.",
                                discarded=len(descartadas),
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

                    relevantes, descartadas = cls._aplicar_filtro_relevancia(jobs)

                    if invalidos:
                        status = ScrapeStatus.PARTIAL
                    elif relevantes:
                        status = ScrapeStatus.SUCCESS
                    else:
                        status = ScrapeStatus.EMPTY  # só havia vagas fora do tema
                    erro = (
                        f"{invalidos} card(s) ignorado(s) por dados incompletos."
                        if invalidos
                        else None
                    )
                    cls._log(
                        f"Resultado: {status.value}; {len(relevantes)} vaga(s); "
                        f"{len(descartadas)} descartada(s) fora do tema"
                    )
                    return ScrapeResult(
                        source=cls.SOURCE,
                        status=status,
                        jobs=relevantes,
                        pages_processed=paginas_processadas,
                        error=erro,
                        discarded=len(descartadas),
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

    @staticmethod
    def _texto(elemento) -> Optional[str]:
        """Texto do elemento sem espaços repetidos; None se vazio ou placeholder."""
        if elemento is None:
            return None
        return valor_ou_none(elemento.get_text(" ", strip=True))

    @classmethod
    def _extrair_local(cls, card) -> Optional[str]:
        """Local do card, sem o balão "A empresa aceita candidaturas de ..."."""
        elemento = card.select_one(VAGAS_LOCATION)
        if elemento is None:
            return None
        for ruido in elemento.select(VAGAS_LOCATION_NOISE):
            ruido.decompose()
        texto = normalizar_espacos(elemento.get_text(" ", strip=True))
        return valor_ou_none(texto.split("A empresa aceita")[0])

    @classmethod
    def _parsear_detalhado(
        cls, html: str, referencia: Optional[date] = None
    ) -> tuple[list[JobSchema], int, int]:
        """Devolve (vagas válidas, cards inválidos, total de cards).

        `referencia` é a data usada para converter "Há N dias"; padrão: hoje.
        Não aplica o filtro de relevância: isso é feito na coleta.
        """
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(VAGAS_JOB_CARD)
        vagas: list[JobSchema] = []
        cards_invalidos = 0
        links_vistos = set()

        for card in cards:
            link_el = card.select_one(VAGAS_TITLE)
            href = (link_el.get("href") or "").strip() if link_el else ""
            # O atributo title vem limpo; o texto do <a> traz espaços extras
            # onde há <mark> ("Engenheiro (a)" em vez de "Engenheiro(a)").
            titulo = ""
            if link_el is not None:
                titulo = normalizar_espacos(
                    link_el.get("title") or link_el.get_text("", strip=False)
                )

            if not titulo or not href:
                cards_invalidos += 1
                continue

            link = urljoin(cls.BASE_URL, href)
            if link in links_vistos:
                continue
            links_vistos.add(link)

            id_externo = link_el.get("data-id-vaga")
            if not id_externo:
                encontrado = cls._ID_NO_LINK.search(href)
                id_externo = encontrado.group(1) if encontrado else None

            qtd_el = card.select_one(VAGAS_POSITIONS)
            qtd_texto = re.search(r"\d+", qtd_el.get_text(" ", strip=True)) if qtd_el else None

            descricao_el = card.select_one(VAGAS_DESCRIPTION)
            data_el = card.select_one(VAGAS_DATE)

            vagas.append(
                JobSchema(
                    titulo=titulo,
                    empresa=cls._texto(card.select_one(VAGAS_COMPANY)),
                    senioridade=cls._texto(card.select_one(VAGAS_SENIORITY)),
                    localizacao=cls._extrair_local(card),
                    # sem separador: o <mark> não pode partir palavras ao meio
                    descricao=(
                        valor_ou_none(descricao_el.get_text("", strip=False))
                        if descricao_el is not None
                        else None
                    ),
                    link=link,
                    origem=cls.SOURCE,
                    raw_payload={"html_fragment": str(card)},
                    id_externo=str(id_externo) if id_externo else None,
                    data_publicacao=(
                        parse_data_vagas(data_el.get_text(" ", strip=True), referencia)
                        if data_el is not None
                        else None
                    ),
                    qtd_posicoes=int(qtd_texto.group()) if qtd_texto else None,
                )
            )

        return vagas, cards_invalidos, len(cards)
