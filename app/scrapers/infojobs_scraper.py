import re
import time
import requests
from bs4 import BeautifulSoup
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper


class InfoJobsScraper(BaseScraper):
    """
    Scraper para infojobs.com.br.

    O portal usa paginação clássica via query string:
        ?page=1 → primeira página
        ?page=2 → segunda página
        ...

    Estratégia de paginação:
        1. Monta a URL com o número da página
        2. Faz a requisição HTTP com requests
        3. Parseia o HTML com BeautifulSoup
        4. Se a página retornar 0 vagas → chegamos ao fim, para o loop
        5. Repete até MAX_PAGES ou fim do conteúdo
    """

    BASE_URL  = (
        "https://www.infojobs.com.br/"
        "empregos.aspx?palabra=cientista%20de%20dados&page={page}"
    )
    MAX_PAGES = 10

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120 Safari/537.36"
        )
    }

    @classmethod
    def coletar(cls) -> list:

        todas_vagas = []

        for page_num in range(1, cls.MAX_PAGES + 1):

            url = cls.BASE_URL.format(page=page_num)
            cls._log(f"Coletando página {page_num}/{cls.MAX_PAGES} → {url}")

            try:
                response = requests.get(url, headers=cls.HEADERS, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                cls._log(f"Erro na requisição da página {page_num}: {e}")
                break

            vagas_pagina = cls._parsear(response.content)

            # Página sem vagas = chegamos ao fim do resultado
            if not vagas_pagina:
                cls._log(f"Página {page_num} sem vagas. Fim da coleta.")
                break

            cls._log(f"Página {page_num}: {len(vagas_pagina)} vagas encontradas")
            todas_vagas.extend(vagas_pagina)

            # Pausa entre requisições para não sobrecarregar o servidor
            time.sleep(1)

        cls._log(f"Total coletado: {len(todas_vagas)} vagas")
        return todas_vagas

    # ── Parser ────────────────────────────────────────────────────────────

    @classmethod
    def _parsear(cls, conteudo: bytes) -> list:
        """Recebe o HTML de uma página e extrai as vagas."""

        soup  = BeautifulSoup(conteudo, "html.parser")
        cards = soup.find_all("div", class_="js_vacancyLoad")
        vagas = []

        for card in cards:

            try:
                titulo = card.find("h2").get_text(" ", strip=True)
            except Exception:
                titulo = "Não informado"

            try:
                empresa_el = card.select_one("div.d-flex.align-items-baseline a")
                empresa    = empresa_el.get_text(strip=True) if empresa_el else "Não informado"
            except Exception:
                empresa = "Não informado"

            try:
                senioridade = "Não informado"
                for ic in card.select("div.d-inline-flex.flex-wrap div"):
                    svg = ic.select_one("svg")
                    if svg and "icon-suitcase" in " ".join(svg.get("class", [])):
                        senioridade = ic.get_text(strip=True)
                        break
            except Exception:
                senioridade = "Não informado"

            try:
                localizacao = "Não informado"
                local_el    = card.select_one("div.mb-8")
                if local_el:
                    for node in local_el.children:
                        texto = str(node).strip()
                        if texto and not texto.startswith("<"):
                            localizacao = re.sub(r"\s+", " ", texto).strip()
                            break
            except Exception:
                localizacao = "Não informado"

            try:
                descricao = "Não informado"
                for d in reversed(card.select("div.text-medium")):
                    if not d.select("svg"):
                        texto = re.sub(r"\s+", " ", d.get_text()).strip()
                        if texto not in ("Hoje", "Ontem"):
                            descricao = texto
                            break
            except Exception:
                descricao = "Não informado"

            try:
                href = card.get("data-href", "")
                link = "https://www.infojobs.com.br" + href if href else None
            except Exception:
                link = None

            # Ignora vagas sem link
            if not link:
                continue

            vagas.append(JobSchema(
                titulo      = titulo,
                empresa     = empresa,
                senioridade = senioridade,
                localizacao = localizacao,
                descricao   = descricao,
                link        = link,
                origem      = "InfoJobs",
            ))

        return vagas