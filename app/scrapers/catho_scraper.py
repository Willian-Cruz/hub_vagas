import time
from datetime import date
from urllib.parse import quote

import requests

from app.schemas.job_schema import JobSchema
from app.scrapers.base_scraper import BaseScraper, ScrapeResult, ScrapeStatus
from app.scrapers.catho_parser import parse_cards


class CathoScraper(BaseScraper):
    """Scraper para listagem de vagas da Catho (catho.com.br).

    A Catho usa paginação tradicional (não infinite scroll). Cada página
    traz um conjunto de <li data-offer-item> que o parser já sabe processar.

    A busca padrão é por "analista de dados" — ajuste TERMOS_BUSCA
    conforme necessário.
    """

    SOURCE = "Catho"
    BASE_URL = "https://www.catho.com.br"
    SEARCH_URL = "https://www.catho.com.br/vagas/{termo}/?page={page}"
    MAX_PAGES = 10
    TIMEOUT = (10, 30)

    # Termos de busca cobrindo o perfil de dados
    TERMOS_BUSCA = [
        "engenheiro-de-dados",
        "analista-de-dados",
        "analytics-engineer",
        "cientista-de-dados",
        "data-engineer",
    ]

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

        for termo in cls.TERMOS_BUSCA:
            for page_num in range(1, cls.MAX_PAGES + 1):
                url = cls.SEARCH_URL.format(termo=quote(termo), page=page_num)
                cls._log(f"Buscando '{termo}' página {page_num}/{cls.MAX_PAGES}")

                try:
                    response = requests.get(
                        url,
                        headers=cls.HEADERS,
                        timeout=cls.TIMEOUT,
                    )
                    response.raise_for_status()
                except requests.RequestException as exc:
                    erro_coleta = f"{termo} p.{page_num}: {type(exc).__name__}: {exc}"
                    cls._log(f"Falha na requisição: {erro_coleta}")
                    break

                paginas_processadas += 1
                html = response.text

                # Verifica estado vazio
                if cls._pagina_sem_resultados(html):
                    cls._log(f"Página {page_num} indica fim da lista para '{termo}'")
                    break

                # Parseia os cards
                cards = parse_cards(html, hoje=date.today())
                if not cards:
                    cls._log(f"Nenhum card encontrado na página {page_num} para '{termo}'")
                    break

                vagas_pagina = []
                for card in cards:
                    job_dict = card.job
                    extra = card.extra

                    link = job_dict["link"]
                    if link in links_vistos:
                        continue
                    links_vistos.add(link)

                    # senioridade já vem do parser (usa classificar_senioridade)
                    senioridade = job_dict["senioridade"]

                    # salário já processado pelo parser
                    salario = job_dict["salario"]

                    # id_externo
                    id_externo = job_dict["id_externo"]

                    # data_publicacao
                    data_pub = job_dict["data_publicacao"]

                    # modalidade - Catho não traz no card, fica None
                    modalidade = None

                    # experiencia, escolaridade, qtd_posicoes
                    experiencia = job_dict.get("experiencia")
                    escolaridade = job_dict.get("escolaridade")
                    qtd_posicoes = job_dict.get("qtd_posicoes")

                    # Construir JobSchema
                    vaga = JobSchema(
                        titulo=job_dict["titulo"],
                        empresa=job_dict["empresa"],
                        senioridade=senioridade,
                        localizacao=job_dict["localizacao"],
                        descricao=job_dict["descricao"],
                        salario=salario,
                        link=link,
                        origem=cls.SOURCE,
                        raw_payload={
                            "html_fragment": job_dict["raw_payload"]["html_fragment"],
                            "senioridade_origem": extra.get("senioridade_origem"),
                            "data_atualizacao": extra.get("data_atualizacao"),
                            "salario_tipo": extra.get("salario_tipo"),
                            "salario_min": extra.get("salario_min"),
                            "salario_max": extra.get("salario_max"),
                            "beneficios_qtd": extra.get("beneficios_qtd"),
                        },
                        id_externo=str(id_externo) if id_externo else None,
                        data_publicacao=data_pub,
                        modalidade=modalidade,
                        experiencia=experiencia,
                        escolaridade=escolaridade,
                        qtd_posicoes=qtd_posicoes,
                    )
                    vagas_pagina.append(vaga)

                if not vagas_pagina:
                    cls._log(f"Página {page_num} para '{termo}' não adicionou vagas novas")
                    break

                todas_vagas.extend(vagas_pagina)
                cls._log(f"Página {page_num} para '{termo}': {len(vagas_pagina)} vaga(s)")

                if page_num < cls.MAX_PAGES:
                    time.sleep(1)

            # Pequena pausa entre termos
            time.sleep(1)

        if erro_coleta and not todas_vagas:
            status = ScrapeStatus.FAILED
        elif erro_coleta:
            status = ScrapeStatus.PARTIAL
        elif not todas_vagas:
            status = ScrapeStatus.EMPTY
        else:
            status = ScrapeStatus.SUCCESS

        cls._log(
            f"Coleta concluída: status={status.value}, vagas={len(todas_vagas)}, "
            f"páginas={paginas_processadas}, erros={erro_coleta or 'nenhum'}"
        )

        return ScrapeResult(
            source=cls.SOURCE,
            status=status,
            jobs=todas_vagas,
            pages_processed=paginas_processadas,
            error=erro_coleta,
            discarded=0,  # Filtro de relevância será aplicado centralmente
        )

    @classmethod
    def _parsear(cls, html: str) -> list[JobSchema]:
        """Extrai vagas do HTML; separado para testes com fixtures."""
        cards = parse_cards(html, hoje=date.today())
        jobs = []
        for card in cards:
            job_dict = card.job
            extra = card.extra
            jobs.append(JobSchema(
                titulo=job_dict["titulo"],
                empresa=job_dict["empresa"],
                senioridade=job_dict["senioridade"],
                localizacao=job_dict["localizacao"],
                descricao=job_dict["descricao"],
                salario=job_dict["salario"],
                link=job_dict["link"],
                origem=cls.SOURCE,
                raw_payload={
                    "html_fragment": job_dict["raw_payload"]["html_fragment"],
                    "senioridade_origem": extra.get("senioridade_origem"),
                },
                id_externo=str(job_dict["id_externo"]) if job_dict["id_externo"] else None,
                data_publicacao=job_dict["data_publicacao"],
                modalidade=job_dict["modalidade"],
                experiencia=job_dict.get("experiencia"),
                escolaridade=job_dict.get("escolaridade"),
                qtd_posicoes=job_dict.get("qtd_posicoes"),
            ))
        return jobs