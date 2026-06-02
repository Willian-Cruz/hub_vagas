import re
import requests
from bs4 import BeautifulSoup
from schemas.job_schema import JobSchema


class InfoJobsScraper:

    @staticmethod
    def coletar():

        url = (
            "https://www.infojobs.com.br/"
            "empregos.aspx?palabra=engenheiro%20de%20dados"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers, timeout=30)

        soup = BeautifulSoup(response.content, "html.parser")

        cards = soup.find_all("div", class_="js_vacancyLoad")

        print(f"InfoJobs - {len(cards)} vagas encontradas")

        vagas = []

        for card in cards:

            try:
                titulo = card.find("h2").get_text(strip=True)
            except:
                titulo = "Não informado"

            try:
                empresa_el = card.select_one("div.d-flex.align-items-baseline a")

                empresa = (
                    empresa_el.get_text(strip=True) if empresa_el else "Não informado"
                )

            except:
                empresa = "Não informado"

            try:

                senioridade = "Não informado"

                for ic in card.select("div.d-inline-flex.flex-wrap div"):

                    svg = ic.select_one("svg")

                    if svg and "icon-suitcase" in " ".join(svg.get("class", [])):

                        senioridade = ic.get_text(strip=True)

                        break

            except:
                senioridade = "Não informado"

            try:

                localizacao = "Não informado"

                local_el = card.select_one("div.mb-8")

                if local_el:

                    for node in local_el.children:

                        texto = str(node).strip()

                        if texto and not texto.startswith("<"):

                            localizacao = re.sub(r"\s+", " ", texto).strip()

                            break

            except:
                localizacao = "Não informado"

            try:

                descricao = "Não informado"

                for d in reversed(card.select("div.text-medium")):

                    if not d.select("svg"):

                        texto = re.sub(r"\s+", " ", d.get_text()).strip()

                        if texto not in ("Hoje", "Ontem"):

                            descricao = texto

                            break

            except:
                descricao = "Não informado"

            try:

                link = "https://www.infojobs.com.br" + card.get("data-href", "")

            except:
                link = "Não informado"

            vaga = JobSchema(
                titulo=titulo,
                empresa=empresa,
                senioridade=senioridade,
                localizacao=localizacao,
                descricao=descricao,
                link=link,
                origem="InfoJobs",
            )

            vagas.append(vaga)

        return vagas