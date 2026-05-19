from playwright.sync_api import sync_playwright
from schemas.job_schema import JobSchema

class VagasScraper:

    @staticmethod
    def coletar():
        
        vagas = []
        
        with sync_playwright() as p:
            
            browser = p.chromium.launch(
                headless=False
            )

            page = browser.new_page()
            page.goto("https://www.google.com/search?q=vagas+engenheiro+de+dados")            
            page.wait_for_timeout(5000)

            vaga=JobSchema(
                titulo="Engenheiro de Dados Jr",
                empresa="Empresa teste",
                localizacao="Essipê",
                descricao="Python SQL AWS Excel Pandas ABNT",
                link=page.url,
                origem="Teste"                 
            )

            vagas.append(vaga)
            
            browser.close()
        
        return vagas