import requests
from bs4 import BeautifulSoup
from schemas.job_schema import JobSchema


class VagasScraper:

    @staticmethod
    def coletar():

        url = "https://www.vagas.com.br/vagas-de-engenheiro-de-dados"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers)

        soup = BeautifulSoup(response.content, "html.parser")

        # PEGA TODAS AS VAGAS
        cards = soup.find_all("li", class_="vaga")

        print(f"Total vagas encontradas: {len(cards)}")

        vagas = []

        for card in cards:

            try:

                titulo = card.find("a", class_="link-detalhes-vaga").get_text(strip=True)

            except:

                titulo = "Não informado"

            try:

                empresa = card.find("span", class_="emprVaga").get_text(strip=True)

            except:

                empresa = "Não informado"

            try:

                senioridade = card.find("span", class_="nivelVaga").get_text(strip=True)

            except:

                senioridade = "Não informado"

            try:

                localizacao = card.find("div", class_="vaga-local").get_text(separator=" ", strip=True)
                localizacao = localizacao.split("A empresa aceita")[0].strip()

            except:

                localizacao = "Não informado"

            try:

                descricao = card.find("div", class_="detalhes").get_text(separator=" ", strip=True)

            except:

                descricao = "Não informado"

            try:

                link = card.find("a", class_="link-detalhes-vaga")["href"]
                link = "https://www.vagas.com.br" + link

            except:

                link = "Não informado"

            print(f"""
                    Título: {titulo}
                    Empresa: {empresa}
                    Senioridade: {senioridade}
                    Localização: {localizacao}
                    Link: {link}
                    --------------------------------
                """)

            vaga = JobSchema(
                titulo=titulo,
                empresa=empresa,
                senioridade=senioridade,
                localizacao=localizacao,
                descricao=descricao,
                link=link,
                origem="Vagas.com",
            )

            vagas.append(vaga)

        return vagas
