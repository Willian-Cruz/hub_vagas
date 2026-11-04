import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from constants.selectors import (
    INFOJOBS_COMPANY,
    INFOJOBS_DATE,
    INFOJOBS_DESCRIPTION,
    INFOJOBS_JOB_CARD,
    INFOJOBS_LOCATION,
    INFOJOBS_LOCATION_NOISE,
    INFOJOBS_METADATA,
    INFOJOBS_METADATA_ICONS,
    INFOJOBS_TITLE,
)
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper, ScrapeResult, ScrapeStatus
from utils.date_utils import parse_data_infojobs
from utils.text_utils import normalizar_espacos, valor_ou_none


class InfoJobsScraper(BaseScraper):
    """Scraper para resultados paginados do InfoJobs."""

    SOURCE = "InfoJobs"
    BASE_URL = (
        "https://www.infojobs.com.br/"
        "empregos.aspx?palabra=engenheiro%20de%20dados&page={page}"
        "&campo=griddate&im=1&orden=desc"
    )
    SITE_URL = "https://www.infojobs.com.br/"
    MAX_PAGES = 10
    TIMEOUT = (10, 30)

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )
    }

    _ID_NO_LINK = re.compile(r"__(\d+)\.aspx")

    @classmethod
    def coletar(cls) -> ScrapeResult:
        todas_vagas: list[JobSchema] = []
        paginas_processadas = 0
        cards_invalidos = 0
        descartadas_total = 0
        erro_coleta = None
        # Links de TODOS os cards válidos já vistos (do tema ou não): é isso que
        # detecta paginação repetida e fim da lista, independente do filtro.
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
                if links_vistos and cards_encontrados == 0:
                    break  # fim normal da paginação
                if not links_vistos and cls._pagina_sem_resultados(response.content):
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
            relevantes, descartadas = cls._aplicar_filtro_relevancia(vagas_novas)
            descartadas_total += len(descartadas)
            todas_vagas.extend(relevantes)
            cls._log(
                f"Página {page_num}: {len(relevantes)} vaga(s) do tema e "
                f"{len(descartadas)} descartada(s) de {len(vagas_pagina)} card(s)"
            )

            if page_num < cls.MAX_PAGES:
                time.sleep(1)

        if erro_coleta:
            status = ScrapeStatus.PARTIAL if links_vistos else ScrapeStatus.FAILED
        elif cards_invalidos:
            status = ScrapeStatus.PARTIAL
            erro_coleta = f"{cards_invalidos} card(s) ignorado(s) por dados incompletos."
        elif todas_vagas:
            status = ScrapeStatus.SUCCESS
        else:
            status = ScrapeStatus.EMPTY

        cls._log(
            f"Resultado: {status.value}; {len(todas_vagas)} vaga(s); "
            f"{descartadas_total} descartada(s) fora do tema; "
            f"{paginas_processadas} página(s) processada(s)"
        )
        return ScrapeResult(
            source=cls.SOURCE,
            status=status,
            jobs=todas_vagas,
            pages_processed=paginas_processadas,
            error=erro_coleta,
            discarded=descartadas_total,
        )

    @classmethod
    def _parsear(cls, conteudo: bytes) -> list[JobSchema]:
        """Extrai vagas do HTML; mantido separado para testes com fixtures."""
        return cls._parsear_detalhado(conteudo)[0]

    @staticmethod
    def _extrair_metadados(card) -> dict:
        """Lê o bloco de metadados pelo ÍCONE de cada item (salário, experiência...)."""
        dados: dict = {}
        for item in card.select(INFOJOBS_METADATA):
            svg = item.select_one("svg")
            classes = svg.get("class", []) if svg else []
            for icone, campo in INFOJOBS_METADATA_ICONS.items():
                if icone in classes and campo not in dados:
                    dados[campo] = valor_ou_none(item.get_text(" ", strip=True))
        return dados

    @staticmethod
    def _extrair_local(card):
        for elemento in card.select(INFOJOBS_LOCATION):
            # O bloco de metadados também tem a classe mb-8: não é o local.
            if elemento.select_one("svg") or "d-inline-flex" in (elemento.get("class") or []):
                continue
            for ruido in elemento.select(INFOJOBS_LOCATION_NOISE):
                ruido.decompose()  # trecho oculto ", 0 Km de você."
            return valor_ou_none(elemento.get_text(" ", strip=True))
        return None

    @staticmethod
    def _extrair_descricao(card):
        for elemento in reversed(card.select(INFOJOBS_DESCRIPTION)):
            classes = elemento.get("class") or []
            # Pula o bloco de metadados (tem ícones) e a data ("30 out").
            if elemento.select_one("svg") or "text-nowrap" in classes:
                continue
            texto = valor_ou_none(elemento.get_text(" ", strip=True))
            if texto and texto.casefold() not in {"hoje", "ontem"}:
                return texto
        return None

    @classmethod
    def _parsear_detalhado(
        cls, conteudo: bytes
    ) -> tuple[list[JobSchema], int, int]:
        """Devolve (vagas válidas, cards inválidos, total de cards).

        Não aplica o filtro de relevância: isso é feito na coleta.
        """
        soup = BeautifulSoup(conteudo, "html.parser")
        cards = soup.select(INFOJOBS_JOB_CARD)
        vagas: list[JobSchema] = []
        cards_invalidos = 0

        for card in cards:
            titulo_el = card.select_one(INFOJOBS_TITLE)
            titulo = normalizar_espacos(titulo_el.get_text(" ", strip=True)) if titulo_el else ""
            href = (card.get("data-href") or "").strip()

            if not titulo or not href:
                cards_invalidos += 1
                continue

            id_externo = card.get("data-id")
            if not id_externo:
                encontrado = cls._ID_NO_LINK.search(href)
                id_externo = encontrado.group(1) if encontrado else None

            empresa_el = card.select_one(INFOJOBS_COMPANY)
            data_el = card.select_one(INFOJOBS_DATE)
            metadados = cls._extrair_metadados(card)

            vagas.append(
                JobSchema(
                    titulo=titulo,
                    empresa=(
                        valor_ou_none(empresa_el.get_text(" ", strip=True))
                        if empresa_el is not None
                        else None
                    ),
                    # O InfoJobs não tem campo de nível; o ícone "suitcase" é
                    # experiência. A senioridade é inferida do título ao salvar.
                    senioridade=None,
                    localizacao=cls._extrair_local(card),
                    descricao=cls._extrair_descricao(card),
                    salario=metadados.get("salario"),
                    link=urljoin(cls.SITE_URL, href),
                    origem=cls.SOURCE,
                    raw_payload={"html_fragment": str(card)},
                    id_externo=str(id_externo) if id_externo else None,
                    data_publicacao=(
                        parse_data_infojobs(data_el.get("data-value"))
                        if data_el is not None
                        else None
                    ),
                    modalidade=metadados.get("modalidade"),
                    experiencia=metadados.get("experiencia"),
                    escolaridade=metadados.get("escolaridade"),
                )
            )

        return vagas, cards_invalidos, len(cards)
