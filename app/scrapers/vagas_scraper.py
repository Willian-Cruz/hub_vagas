import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper


class VagasScraper(BaseScraper):
    """
    Scraper para vagas.com.br.

    O portal usa infinite scroll com JavaScript:
    novas vagas são carregadas via requisição assíncrona
    conforme o usuário rola a página até o fim.

    Estratégia de paginação:
        1. Abre o browser headless com Playwright
        2. Rola até o fim da página (dispara o lazy-load)
        3. Aguarda novas vagas aparecerem no DOM
        4. Repete até não haver novas vagas ou atingir MAX_PAGES scrolls
        5. Com todo o conteúdo carregado, parseia o HTML final com BeautifulSoup
    """

    URL       = "https://www.vagas.com.br/vagas-de-cientista-de-dados"
    MAX_PAGES = 20  # número máximo de scrolls (cada scroll ≈ 1 "página")

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    @classmethod
    def coletar(cls) -> list:

        vagas = []

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)
            page    = browser.new_page(user_agent=cls.HEADERS["User-Agent"])

            try:
                cls._log(f"Acessando {cls.URL}")
                page.goto(cls.URL, timeout=40_000)
                page.wait_for_load_state("networkidle", timeout=20_000)

                scroll_count    = 0
                sem_novidade    = 0      # quantas vezes seguidas não apareceu nada novo
                MAX_SEM_NOVIDADE = 3     # para após 3 scrolls consecutivos sem resultado

                while scroll_count < cls.MAX_PAGES:

                    vagas_antes = len(page.query_selector_all("li.vaga"))

                    # Rola até o final para disparar o lazy-load
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                    # Aguarda até aparecer pelo menos uma vaga nova (ou timeout de 6s)
                    try:
                        page.wait_for_function(
                            f"document.querySelectorAll('li.vaga').length > {vagas_antes}",
                            timeout=6_000,
                        )
                        sem_novidade = 0  # reset: apareceu coisa nova
                    except PlaywrightTimeout:
                        sem_novidade += 1
                        cls._log(
                            f"Scroll {scroll_count + 1}: sem novas vagas "
                            f"({sem_novidade}/{MAX_SEM_NOVIDADE})"
                        )
                        if sem_novidade >= MAX_SEM_NOVIDADE:
                            cls._log("Fim da lista detectado.")
                            break

                    vagas_depois = len(page.query_selector_all("li.vaga"))
                    cls._log(
                        f"Scroll {scroll_count + 1}/{cls.MAX_PAGES} — "
                        f"{vagas_depois} vagas carregadas"
                    )

                    scroll_count += 1

                    # Pequena pausa para não sobrecarregar o servidor
                    time.sleep(0.5)

                # Com todo o conteúdo carregado, parseia o HTML final
                html  = page.content()
                vagas = cls._parsear(html)

            except Exception as e:
                cls._log(f"Erro durante a coleta: {e}")

            finally:
                browser.close()

        cls._log(f"Total coletado: {len(vagas)} vagas")
        return vagas

    # ── Parser ────────────────────────────────────────────────────────────

    @classmethod
    def _parsear(cls, html: str) -> list:
        """Recebe o HTML completo e extrai todas as vagas."""

        soup  = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("li", class_="vaga")
        vagas = []

        for card in cards:

            try:
                titulo = card.find("a", class_="link-detalhes-vaga").get_text(" ", strip=True)
            except Exception:
                titulo = "Não informado"

            try:
                empresa = card.find("span", class_="emprVaga").get_text(strip=True)
            except Exception:
                empresa = "Não informado"

            try:
                senioridade = card.find("span", class_="nivelVaga").get_text(strip=True)
            except Exception:
                senioridade = "Não informado"

            try:
                localizacao = card.find("div", class_="vaga-local").get_text(separator=" ", strip=True)
                localizacao = localizacao.split("A empresa aceita")[0].strip()
            except Exception:
                localizacao = "Não informado"

            try:
                descricao = card.find("div", class_="detalhes").get_text(separator=" ", strip=True)
            except Exception:
                descricao = "Não informado"

            try:
                href = card.find("a", class_="link-detalhes-vaga")["href"]
                link = "https://www.vagas.com.br" + href
            except Exception:
                link = None

            # Ignora vagas sem link (campo único no banco — não seriam salvas)
            if not link:
                continue

            vagas.append(JobSchema(
                titulo      = titulo,
                empresa     = empresa,
                senioridade = senioridade,
                localizacao = localizacao,
                descricao   = descricao,
                link        = link,
                origem      = "Vagas.com",
            ))

        return vagas