import copy
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.constants.selectors import (
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
from app.schemas.job_schema import JobSchema
from app.scrapers.base_scraper import BaseScraper
from app.utils.date_utils import parse_data_infojobs
from app.utils.text_utils import normalizar_espacos, valor_ou_none


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

    # ── Template Method: filhos implementam ──────────────────────────────

    @classmethod
    def _buscar_pagina(cls, numero_pagina: int) -> bytes:
        """Faz o request HTTP da página paginada do InfoJobs."""
        url = cls.BASE_URL.format(page=numero_pagina)
        ca_bundle = (
            os.getenv("REQUESTS_CA_BUNDLE")
            or os.getenv("CURL_CA_BUNDLE")
            or True
        )
        response = requests.get(
            url,
            headers=cls.HEADERS,
            timeout=cls.TIMEOUT,
            verify=ca_bundle,
        )
        response.raise_for_status()
        return response.content

    @classmethod
    def _parsear_cards(
        cls, conteudo: bytes
    ) -> tuple[list[JobSchema], int, int]:
        """Extrai (vagas válidas, cards inválidos, total de cards) do HTML."""
        return cls._parsear_detalhado(conteudo)

    # ── Helpers de parse (filho) ─────────────────────────────────────────

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
            if elemento.select_one("svg") or "d-inline-flex" in (elemento.get("class") or []):
                continue
            local = copy.copy(elemento)
            for ruido in local.select(INFOJOBS_LOCATION_NOISE):
                ruido.decompose()
            return valor_ou_none(local.get_text(" ", strip=True))
        return None

    @staticmethod
    def _extrair_descricao(card):
        for elemento in reversed(card.select(INFOJOBS_DESCRIPTION)):
            classes = elemento.get("class") or []
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

            html_fragment = str(card)

            id_externo = card.get("data-id")
            if not id_externo:
                encontrado = cls._ID_NO_LINK.search(href)
                id_externo = encontrado.group(1) if encontrado else None

            empresa_el = card.select_one(INFOJOBS_COMPANY)
            data_el = card.select_one(INFOJOBS_DATE)
            metadados = cls._extrair_metadados(card)
            descricao = cls._extrair_descricao(card)
            experiencia = metadados.get("experiencia")

            senioridade_nivel = None
            senioridade_origem = None

            vagas.append(
                JobSchema(
                    titulo=titulo,
                    empresa=(
                        valor_ou_none(empresa_el.get_text(" ", strip=True))
                        if empresa_el is not None
                        else None
                    ),
                    senioridade=senioridade_nivel,
                    localizacao=cls._extrair_local(card),
                    descricao=descricao,
                    salario=metadados.get("salario"),
                    link=urljoin(cls.SITE_URL, href),
                    origem=cls.SOURCE,
                    raw_payload={
                        "html_fragment": html_fragment,
                        "senioridade_origem": senioridade_origem,
                    },
                    id_externo=str(id_externo) if id_externo else None,
                    data_publicacao=(
                        parse_data_infojobs(data_el.get("data-value"))
                        if data_el is not None
                        else None
                    ),
                    modalidade=metadados.get("modalidade"),
                    experiencia=experiencia,
                    escolaridade=metadados.get("escolaridade"),
                )
            )

        return vagas, cards_invalidos, len(cards)
