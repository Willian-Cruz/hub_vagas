import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper


class VagasScraper(BaseScraper):
    """
    Scraper para vagas.com.br.

    O portal usa infinite scroll com JavaScript:
    novas vagas sao carregadas via requisicao assincrona
    conforme o usuario rola a pagina ate o fim.

    Estrategia de paginacao:
        1. Abre o browser headless com Playwright
        2. Aguarda os cards 'li.vaga' aparecerem no DOM
        3. Rola ate o fim da pagina (dispara o lazy-load)
        4. Aguarda novas vagas aparecerem no DOM
        5. Repete ate nao haver novas vagas ou atingir MAX_PAGES scrolls
        6. Com todo o conteudo carregado, parseia o HTML final com BeautifulSoup
    """

    URL       = "https://www.vagas.com.br/vagas-de-analista-de-dados"
    MAX_PAGES = 20

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    @classmethod
    def coletar(cls) -> list:

        vagas = []

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False,   # vagas.com.br bloqueia headless via bot-detection.
                                  # Headed mode contorna isso sem impacto para pipeline local.
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            context = browser.new_context(
                user_agent=cls.USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                locale="pt-BR",
            )

            page = context.new_page()

            # Remove a flag navigator.webdriver que identifica browsers headless
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            try:
                cls._log(f"Acessando {cls.URL}")

                # domcontentloaded dispara assim que o HTML e parseado pelo browser —
                # nao espera scripts, imagens, nem tracking pixels terminarem.
                # Muito mais confiavel que networkidle em portais modernos.
                page.goto(cls.URL, timeout=40_000, wait_until="domcontentloaded")

                # Aguarda os cards de vaga aparecerem no DOM.
                # Se der timeout aqui, a pagina nao carregou ou mudou de estrutura.
                cls._log("Aguardando cards de vaga...")
                try:
                    page.wait_for_selector("li.vaga", timeout=25_000)
                    cls._log("Cards detectados — iniciando scroll")
                except PlaywrightTimeout:
                    cls._log(
                        "Nenhum card 'li.vaga' encontrado. "
                        "O portal pode estar bloqueando a coleta ou "
                        "a estrutura HTML foi alterada."
                    )
                    return []

                scroll_count     = 0
                sem_novidade     = 0
                MAX_SEM_NOVIDADE = 3

                while scroll_count < cls.MAX_PAGES:

                    vagas_antes = len(page.query_selector_all("li.vaga"))

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                    try:
                        page.wait_for_function(
                            f"document.querySelectorAll('li.vaga').length > {vagas_antes}",
                            timeout=6_000,
                        )
                        sem_novidade = 0
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
                        f"Scroll {scroll_count + 1}/{cls.MAX_PAGES} - "
                        f"{vagas_depois} vagas carregadas"
                    )

                    scroll_count += 1
                    time.sleep(0.5)

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