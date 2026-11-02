import re
import time
from urllib.parse import quote, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from schemas.job_schema import JobSchema
from scrapers.base_scraper import BaseScraper, ScrapeResult, ScrapeStatus


class GupyScraper(BaseScraper):
    """
    Scraper para o Portal de Vagas da Gupy (portal.gupy.io).

    A Gupy é um ATS usado por milhares de empresas no Brasil — cada empresa
    tem seu próprio subdomínio (ex: empresa.gupy.io/jobs/123), e o Portal de
    Vagas (portal.gupy.io/job-search) agrega a busca entre todas elas.

    O portal é uma SPA em Next.js: o HTML inicial não traz vaga nenhuma —
    a lista chega via chamada assíncrona depois que a página carrega no
    navegador. Mesmo caso do vagas.com.br, só que sem fallback nenhum no
    HTML estático (nem o "0 resultado" que aparece é real).

    Estratégia de paginação: infinite scroll, igual ao VagasScraper.

    Estratégia de extração (dois níveis):
        Nível 1 — tenta achar cards estruturados (um container com um <a>
                  de vaga + um heading dentro) e extrai título/local/descrição
                  do texto ao redor.
        Nível 2 — fallback: qualquer <a> cujo href bata com o padrão
                  https://<empresa>.gupy.io/jobs/<id> é, por definição, uma
                  vaga. Não é bonito, mas não depende de nomes de classe.

    Por que dois níveis em vez de um seletor CSS fixo (como nos outros
    scrapers)?
        A Gupy usa CSS-in-JS (classes tipo "zVzmE", geradas no build) —
        essas classes mudam a cada deploy da Gupy, então fixar um seletor
        exato quebraria em pouco tempo. O nível 2 usa o único padrão
        realmente estável: a URL da vaga sempre segue /jobs/<id>.

    IMPORTANTE — isto não foi testado contra o site real:
        gupy.io não está na allowlist de rede do sandbox onde este código
        foi escrito, então não consegui abrir o portal e conferir o DOM de
        verdade. Rode localmente com HEADLESS = False, abra o DevTools em
        cima de um card de vaga e me mande a estrutura — ajusto o Nível 1
        num segundo. O Nível 2 garante que a coleta não fica zerada nesse
        meio tempo.
    """

    BASE_URL = "https://portal.gupy.io/job-search/term={termo}&workplaceTypes[]=remote"
    SOURCE = "Gupy"

    # Termos cobrindo o perfil (analista de dados → engenharia de dados).
    # Adicione/remova termos aqui conforme o que você quiser rastrear.
    TERMOS_BUSCA = [
        "engenheiro de dados",
        "analista de dados",
        "analytics engineer",
    ]

    MAX_PAGES = 20     # scrolls por termo de busca
    HEADLESS = True

    JOB_LINK_PATTERN = re.compile(r"https?://[\w.-]+\.gupy\.io/jobs/\d+")

    _SENIORIDADE_HINT = re.compile(
        r"est[aá]gi[aá]rio|trainee|j[uú]nior|jr\.?|pleno|pl\.?|"
        r"s[eê]nior|senior|sr\.?|especialista",
        re.IGNORECASE,
    )

    # ── Coleta ───────────────────────────────────────────────────────────

    @classmethod
    def coletar(cls) -> ScrapeResult:
        vagas_por_link = {}
        erros = []
        buscas_processadas = 0
        browser = None

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=cls.HEADLESS)
                try:
                    page = browser.new_page()

                    for termo in cls.TERMOS_BUSCA:
                        url = cls.BASE_URL.format(termo=quote(termo))
                        cls._log(f"Buscando termo '{termo}' → {url}")

                        try:
                            html = cls._carregar_pagina(page, url)
                            buscas_processadas += 1
                            vagas_termo = cls._parsear(html)
                            cls._log(
                                f"Termo '{termo}': {len(vagas_termo)} vagas"
                            )

                            for vaga in vagas_termo:
                                vagas_por_link[vaga.link] = vaga
                        except Exception as erro:
                            erros.append(f"{termo}: {erro}")
                            cls._log(f"Erro buscando '{termo}': {erro}")

                        time.sleep(1)
                finally:
                    if browser is not None:
                        browser.close()
        except Exception as erro:
            erros.append(str(erro))

        vagas = list(vagas_por_link.values())
        if erros:
            status = ScrapeStatus.PARTIAL if vagas else ScrapeStatus.FAILED
        else:
            status = ScrapeStatus.SUCCESS if vagas else ScrapeStatus.EMPTY

        resultado = ScrapeResult(
            source=cls.SOURCE,
            status=status,
            jobs=vagas,
            pages_processed=buscas_processadas,
            error="; ".join(erros) if erros else None,
        )
        cls._log(
            f"Coleta concluída: status={resultado.status.value}, "
            f"vagas={len(resultado.jobs)}, buscas={resultado.pages_processed}"
        )
        return resultado

    # ── Carregamento (infinite scroll) ──────────────────────────────────

    @classmethod
    def _carregar_pagina(cls, page, url: str) -> str:
        """Abre a URL e rola até parar de carregar novas vagas."""

        scroll_count      = 0
        sem_novidade      = 0
        MAX_SEM_NOVIDADE  = 3
        seletor_link      = "a[href*='.gupy.io/jobs/']"

        page.goto(url, timeout=40_000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector(seletor_link, timeout=12_000)
        except PlaywrightTimeout:
            if cls._pagina_sem_resultados(page.content()):
                return page.content()

        while scroll_count < cls.MAX_PAGES:

            links_antes = len(page.query_selector_all(seletor_link))

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            try:
                page.wait_for_function(
                    f"document.querySelectorAll(\"{seletor_link}\").length > {links_antes}",
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

            scroll_count += 1
            time.sleep(0.5)

        return page.content()

    # ── Parser ───────────────────────────────────────────────────────────

    @classmethod
    def _parsear(cls, html: str) -> list:
        """Recebe o HTML já renderizado e extrai as vagas (nível 1 → nível 2)."""

        soup = BeautifulSoup(html, "html.parser")

        vagas = cls._parsear_nivel1(soup)
        if not vagas:
            vagas = cls._parsear_nivel2(soup)

        return vagas

    @classmethod
    def _parsear_nivel1(cls, soup: BeautifulSoup) -> list:
        """Tenta achar cards estruturados: um item de lista contendo o link da vaga."""

        vagas = []

        for card in soup.select("li"):

            link_el = card.find("a", href=cls.JOB_LINK_PATTERN)
            if not link_el:
                continue

            link = link_el["href"].split("?")[0]

            titulo_el = card.find(["h2", "h3"])
            titulo    = (titulo_el.get_text(strip=True) if titulo_el
                         else link_el.get_text(strip=True))

            if not titulo:
                continue

            textos      = [t.get_text(" ", strip=True) for t in card.find_all(["p", "span"])]
            localizacao = next((t for t in textos if cls._parece_local(t)), "Não informado")
            descricao   = " ".join(t for t in textos if t) or "Não informado"

            vagas.append(JobSchema(
                titulo      = titulo,
                empresa     = cls._empresa_da_url(link),
                senioridade = cls._extrair_senioridade(titulo),
                localizacao = localizacao,
                descricao   = descricao,
                link        = link,
                origem      = "Gupy",
            ))

        return vagas

    @classmethod
    def _parsear_nivel2(cls, soup: BeautifulSoup) -> list:
        """Fallback: qualquer link /jobs/<id> vira vaga, mesmo sem card identificável."""

        vagas  = []
        vistos = set()

        for link_el in soup.find_all("a", href=cls.JOB_LINK_PATTERN):

            link = link_el["href"].split("?")[0]
            if link in vistos:
                continue
            vistos.add(link)

            titulo = link_el.get_text(strip=True)
            if not titulo:
                pai    = link_el.find_parent()
                titulo = pai.get_text(" ", strip=True)[:120] if pai else ""

            titulo = titulo or "Não informado"

            vagas.append(JobSchema(
                titulo      = titulo,
                empresa     = cls._empresa_da_url(link),
                senioridade = cls._extrair_senioridade(titulo),
                localizacao = "Não informado",
                descricao   = "Não informado",
                link        = link,
                origem      = "Gupy",
            ))

        return vagas

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _empresa_da_url(link: str) -> str:
        """Extrai o nome da empresa do subdomínio (ex: mobi7.gupy.io → Mobi7)."""

        host       = urlparse(link).hostname or ""
        subdominio = host.split(".gupy.io")[0]
        return subdominio.replace("-", " ").title() if subdominio else "Não informado"

    @classmethod
    def _extrair_senioridade(cls, titulo: str) -> str:
        """Puxa a palavra de senioridade do título (normalização real fica no pipeline)."""

        match = cls._SENIORIDADE_HINT.search(titulo)
        return match.group(0) if match else "Não informado"

    @staticmethod
    def _parece_local(texto: str) -> bool:
        """Heurística simples para reconhecer texto de localização entre os textos do card."""

        if not texto or len(texto) > 60:
            return False

        padrao = re.compile(
            r"(?i:remoto|remote|h[ií]brido|home office|presencial)|\b[A-Z]{2}\b"
        )
        return bool(padrao.search(texto))
