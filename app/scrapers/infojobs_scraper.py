import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from constants.selectors import (
    INFOJOBS_COMPANY,
    INFOJOBS_DESCRIPTION,
    INFOJOBS_JOB_CARD,
    INFOJOBS_LOCATION,
    INFOJOBS_METADATA,
    INFOJOBS_TITLE,
)
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper, ScrapeResult, ScrapeStatus


class InfoJobsScraper(BaseScraper):
    """Scraper para resultados paginados do InfoJobs."""

    SOURCE = "InfoJobs"
    BASE_URL = (
        "https://www.infojobs.com.br/"
        "empregos.aspx?palabra=engenheiro%20de%20dados&page={page}"
        "&campo=griddate&im=1&orden=desc"
    )
    MAX_PAGES = 10
    TIMEOUT = (10, 30)

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )
    }

    @classmethod
    def coletar(cls) -> ScrapeResult:
        todas_vagas: list[JobSchema] = []
        paginas_processadas = 0
        cards_invalidos = 0
        erro_coleta = None
        links_vistos: set[str] = set()

        # Requests mantém TLS habilitado. Em redes com proxy, a CA confiável
        # pode ser informada por REQUESTS_CA_BUNDLE ou CURL_CA_BUNDLE.
        ca_bundle = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("CURL_CA_BUNDLE") or True

        for page_num in range(1, cls.MAX_PAGES + 1):
            url = cls.BASE_URL.format(page=page_num)
            cls._log(f"Coletando página {page_num}/{cls.MAX_PAGES}")

            try:
                response = requests.get(
                    url,
                    headers=cls.HEADERS,
                    timeout=cls.TIMEOUT,
                    verify=ca_bundle,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                erro_coleta = f"Página {page_num}: {type(exc).__name__}: {exc}"
                cls._log(f"Falha na requisição: {erro_coleta}")
                break

            paginas_processadas += 1
            vagas_pagina, invalidos, cards_encontrados = cls._parsear_detalhado(
                response.content
            )
            cards_invalidos += invalidos

            if not vagas_pagina:
                if todas_vagas and cards_encontrados == 0:
                    break  # fim normal da paginação
                if not todas_vagas and cls._pagina_sem_resultados(response.content):
                    break  # estado vazio explícito do portal
                if cards_encontrados == 0:
                    erro_coleta = (
                        f"A página não contém o seletor esperado "
                        f"'{INFOJOBS_JOB_CARD}'."
                    )
                elif invalidos:
                    erro_coleta = (
                        f"{invalidos} card(s) sem título ou link válido."
                    )
                break

            vagas_novas = [
                vaga for vaga in vagas_pagina if vaga.link not in links_vistos
            ]
            if not vagas_novas:
                cls._log(
                    f"Página {page_num} repetiu links anteriores; encerrando paginação."
                )
                break

            links_vistos.update(vaga.link for vaga in vagas_novas)
            todas_vagas.extend(vagas_novas)
            cls._log(
                f"Página {page_num}: {len(vagas_novas)} vaga(s) nova(s) "
                f"de {len(vagas_pagina)} card(s)"
            )

            if page_num < cls.MAX_PAGES:
                time.sleep(1)

        if erro_coleta:
            status = ScrapeStatus.PARTIAL if todas_vagas else ScrapeStatus.FAILED
        elif cards_invalidos:
            status = ScrapeStatus.PARTIAL
            erro_coleta = f"{cards_invalidos} card(s) ignorado(s) por dados incompletos."
        elif todas_vagas:
            status = ScrapeStatus.SUCCESS
        else:
            status = ScrapeStatus.EMPTY

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
        )

    @classmethod
    def _parsear(cls, conteudo: bytes) -> list[JobSchema]:
        """Extrai vagas do HTML; mantido separado para testes com fixtures."""
        return cls._parsear_detalhado(conteudo)[0]

    @classmethod
    def _parsear_detalhado(
        cls, conteudo: bytes
    ) -> tuple[list[JobSchema], int, int]:
        soup = BeautifulSoup(conteudo, "html.parser")
        cards = soup.select(INFOJOBS_JOB_CARD)
        vagas: list[JobSchema] = []
        cards_invalidos = 0

        for card in cards:
            titulo_el = card.select_one(INFOJOBS_TITLE)
            titulo = titulo_el.get_text(" ", strip=True) if titulo_el else ""
            href = (card.get("data-href") or "").strip()

            if not titulo or not href:
                cards_invalidos += 1
                continue

            empresa_el = card.select_one(INFOJOBS_COMPANY)
            empresa = (
                empresa_el.get_text(" ", strip=True)
                if empresa_el
                else "Não informado"
            )

            senioridade = "Não informado"
            for item in card.select(INFOJOBS_METADATA):
                svg = item.select_one("svg")
                classes_svg = svg.get("class", []) if svg else []
                if "icon-suitcase" in classes_svg:
                    senioridade = item.get_text(" ", strip=True)
                    break

            local_el = card.select_one(INFOJOBS_LOCATION)
            localizacao = (
                re.sub(r"\s+", " ", local_el.get_text(" ", strip=True))
                if local_el
                else "Não informado"
            )

            descricao = "Não informado"
            for descricao_el in reversed(card.select(INFOJOBS_DESCRIPTION)):
                texto = re.sub(
                    r"\s+", " ", descricao_el.get_text(" ", strip=True)
                )
                if texto.casefold() not in {"hoje", "ontem"} and texto:
                    descricao = texto
                    break

            vagas.append(
                JobSchema(
                    titulo=titulo,
                    empresa=empresa or "Não informado",
                    senioridade=senioridade,
                    localizacao=localizacao or "Não informado",
                    descricao=descricao,
                    link=urljoin("https://www.infojobs.com.br/", href),
                    origem=cls.SOURCE,
                )
            )

        return vagas, cards_invalidos, len(cards)
