"""
Testes unitários para os scrapers (refatoração Sprint 6.5).

Estratégia:
    Testamos apenas o método _parsear() de cada scraper,
    passando HTML fixo que simula o que o portal retornaria.
    Isso evita dependência de rede e torna os testes rápidos e estáveis.

    Os testes de coletar() mockam _buscar_pagina() e _parsear_cards()
    (Template Method do BaseScraper), não requests/playwright diretamente.

Execução: pytest tests/test_scrapers.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
import requests
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from scrapers.base_scraper import ScrapeStatus
from scrapers.vagas_scraper import VagasScraper
from scrapers.infojobs_scraper import InfoJobsScraper
from scrapers.gupy_scraper import GupyScraper
from schemas.job_schema import JobSchema


# ════════════════════════════════════════════════════════════════
# HTML FIXTURES — simulam o que os portais retornam
# ════════════════════════════════════════════════════════════════

VAGAS_HTML_UMA_VAGA = """
<ul>
  <li class="vaga">
    <a class="link-detalhes-vaga" href="/vaga-engenheiro-de-dados-1234">
      Engenheiro de Dados Pleno
    </a>
    <span class="emprVaga">Empresa XYZ</span>
    <span class="nivelVaga">Pleno</span>
    <div class="vaga-local">São Paulo - SP</div>
    <div class="detalhes">Experiência em Python e SQL.</div>
  </li>
</ul>
"""

VAGAS_HTML_MULTIPLAS = """
<ul>
  <li class="vaga">
    <a class="link-detalhes-vaga" href="/vaga-1">Engenheiro de Dados Sr</a>
    <span class="emprVaga">Empresa A</span>
    <span class="nivelVaga">Sênior</span>
    <div class="vaga-local">Remoto</div>
    <div class="detalhes">Spark, Airflow, AWS.</div>
  </li>
  <li class="vaga">
    <a class="link-detalhes-vaga" href="/vaga-2">Analista de Dados Jr</a>
    <span class="emprVaga">Empresa B</span>
    <span class="nivelVaga">Júnior</span>
    <div class="vaga-local">Rio de Janeiro - RJ</div>
    <div class="detalhes">Power BI, Excel.</div>
  </li>
  <li class="vaga">
    <a class="link-detalhes-vaga" href="/vaga-3">Data Engineer</a>
    <span class="emprVaga">Empresa C</span>
    <span class="nivelVaga">Pleno</span>
    <div class="vaga-local">Curitiba - PR</div>
    <div class="detalhes">Python, dbt, BigQuery.</div>
  </li>
</ul>
"""

VAGAS_HTML_SEM_LINK = """
<ul>
  <li class="vaga">
    <span class="emprVaga">Empresa Sem Link</span>
    <span class="nivelVaga">Pleno</span>
    <div class="vaga-local">São Paulo - SP</div>
    <div class="detalhes">Sem link de acesso.</div>
  </li>
</ul>
"""

VAGAS_HTML_VAZIO = "<ul></ul>"

INFOJOBS_HTML_UMA_VAGA = """
<div class="js_vacancyLoad" data-href="/vaga-infojobs-5678">
  <h2>Engenheiro de Dados</h2>
  <div class="d-flex align-items-baseline">
    <a href="#">Empresa IJ</a>
  </div>
  <div class="mb-8">Rio de Janeiro - RJ</div>
  <div class="text-medium">Kafka, Python, Cloud.</div>
</div>
"""

INFOJOBS_HTML_MULTIPLAS = """
<div class="js_vacancyLoad" data-href="/vaga-ij-1">
  <h2>Data Engineer Sr</h2>
  <div class="d-flex align-items-baseline"><a href="#">Alpha Corp</a></div>
  <div class="mb-8">São Paulo - SP</div>
  <div class="text-medium">Databricks, Spark, Azure.</div>
</div>
<div class="js_vacancyLoad" data-href="/vaga-ij-2">
  <h2>Analista BI</h2>
  <div class="d-flex align-items-baseline"><a href="#">Beta Inc</a></div>
  <div class="mb-8">Remoto</div>
  <div class="text-medium">Power BI, SQL Server.</div>
</div>
"""

INFOJOBS_HTML_VAZIO = "<div></div>"

GUPY_HTML_NIVEL1_UMA_VAGA = """
<ul>
  <li>
    <a href="https://mobi7.gupy.io/jobs/10768550?jobBoardSource=gupy_public_page">Ver vaga</a>
    <h2>Engenheiro de Dados Júnior</h2>
    <p>Mobi7</p>
    <span>Remoto</span>
    <p>SQL, Python, AWS.</p>
  </li>
</ul>
"""

GUPY_HTML_NIVEL1_MULTIPLAS = """
<ul>
  <li>
    <a href="https://mobi7.gupy.io/jobs/10768550">Ver vaga</a>
    <h2>Engenheiro de Dados Júnior</h2>
    <p>Mobi7</p>
    <span>Remoto</span>
  </li>
  <li>
    <a href="https://yduqstech.gupy.io/jobs/11111565">Ver vaga</a>
    <h2>Analista de Dados Pleno</h2>
    <p>Yduqs</p>
    <span>São Paulo - SP</span>
  </li>
  <li>
    <a href="https://localiza.gupy.io/jobs/11113610">Ver vaga</a>
    <h2>Engenheiro de Dados Sênior</h2>
    <p>Localiza</p>
    <span>Remoto</span>
  </li>
</ul>
"""

GUPY_HTML_NIVEL1_SEM_LINK_VAGA = """
<ul>
  <li>
    <a href="/job-search/state=São Paulo">São Paulo</a>
    <h2>Vagas por estado</h2>
  </li>
</ul>
"""

GUPY_HTML_NIVEL2_FALLBACK = """
<div>
  <div class="sc-xk93hj-ghost-class">
    <a href="https://localiza.gupy.io/jobs/11015637">ENGENHEIRO DE DADOS SÊNIOR | REMOTO</a>
  </div>
</div>
"""

GUPY_HTML_NIVEL2_LINK_DUPLICADO = """
<div>
  <a href="https://x.gupy.io/jobs/1?jobBoardSource=a">Vaga X</a>
  <a href="https://x.gupy.io/jobs/1?jobBoardSource=b">Vaga X de novo</a>
</div>
"""

GUPY_HTML_VAZIO = "<div></div>"


# ════════════════════════════════════════════════════════════════
# TESTES — VagasScraper.parsear
# ════════════════════════════════════════════════════════════════

class TestVagasScraperParsear:

    def test_retorna_lista(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert isinstance(resultado, list)

    def test_extrai_uma_vaga(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert len(resultado) == 1

    def test_extrai_multiplas_vagas(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_MULTIPLAS)
        assert len(resultado) == 3

    def test_retorna_job_schema(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert isinstance(resultado[0], JobSchema)

    def test_titulo_correto(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert "Engenheiro de Dados" in resultado[0].titulo

    def test_empresa_correta(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert resultado[0].empresa == "Empresa XYZ"

    def test_link_completo(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert resultado[0].link.startswith("https://www.vagas.com.br")

    def test_origem_correta(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA)
        assert resultado[0].origem == "Vagas.com"

    def test_ignora_vaga_sem_link(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_SEM_LINK)
        assert len(resultado) == 0

    def test_html_vazio_retorna_lista_vazia(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_VAZIO)
        assert resultado == []


# ════════════════════════════════════════════════════════════════
# TESTES — InfoJobsScraper.parsear
# ════════════════════════════════════════════════════════════════

class TestInfoJobsScraperParsear:

    def test_retorna_lista(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_UMA_VAGA.encode())
        assert isinstance(resultado, list)

    def test_extrai_uma_vaga(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_UMA_VAGA.encode())
        assert len(resultado) == 1

    def test_extrai_multiplas_vagas(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_MULTIPLAS.encode())
        assert len(resultado) == 2

    def test_retorna_job_schema(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_UMA_VAGA.encode())
        assert isinstance(resultado[0], JobSchema)

    def test_titulo_correto(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_UMA_VAGA.encode())
        assert "Engenheiro de Dados" in resultado[0].titulo

    def test_link_completo(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_UMA_VAGA.encode())
        assert resultado[0].link.startswith("https://www.infojobs.com.br")

    def test_origem_correta(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_UMA_VAGA.encode())
        assert resultado[0].origem == "InfoJobs"

    def test_html_vazio_retorna_lista_vazia(self):
        resultado = InfoJobsScraper._parsear(INFOJOBS_HTML_VAZIO.encode())
        assert resultado == []

    def test_aceita_href_absoluto(self):
        html = INFOJOBS_HTML_UMA_VAGA.replace(
            'data-href="/vaga-infojobs-5678"',
            'data-href="https://carreiras.example/vagas/5678"',
        )
        resultado = InfoJobsScraper._parsear(html.encode())
        assert resultado[0].link == "https://carreiras.example/vagas/5678"

    def test_campo_opcional_ausente_usa_padrao(self):
        html = INFOJOBS_HTML_UMA_VAGA.replace(
            '<div class="mb-8">Rio de Janeiro - RJ</div>', ""
        )
        resultado = InfoJobsScraper._parsear(html.encode())
        assert resultado[0].localizacao is None


# ════════════════════════════════════════════════════════════════
# TESTES — VagasScraper.coletar (Template Method)
# ════════════════════════════════════════════════════════════════

class TestVagasScraperColetar:

    def test_aguarda_dom_e_retorna_resultado_estruturado(self, monkeypatch):
        monkeypatch.setattr(VagasScraper, "MAX_PAGES", 1)
        monkeypatch.setattr(
            VagasScraper, "_buscar_pagina",
            lambda pagina: VAGAS_HTML_UMA_VAGA
        )
        monkeypatch.setattr(
            VagasScraper, "_parsear_cards",
            lambda conteudo: VagasScraper._parsear_detalhado(conteudo)
        )
        monkeypatch.setattr("time.sleep", lambda *_: None)

        resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 1
        assert resultado.pages_processed == 1
        assert "ordenar_por=mais_recentes" in VagasScraper.URL

    def test_estado_vazio_retorna_empty(self, monkeypatch):
        html = "<p>Nenhuma vaga encontrada nesta busca</p>"
        monkeypatch.setattr(VagasScraper, "MAX_PAGES", 1)
        monkeypatch.setattr(
            VagasScraper, "_buscar_pagina",
            lambda pagina: html
        )
        monkeypatch.setattr(
            VagasScraper, "_parsear_cards",
            lambda conteudo: ([], 0, 0)
        )
        monkeypatch.setattr("time.sleep", lambda *_: None)

        resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.EMPTY
        assert resultado.pages_processed == 1

    def test_sem_cards_e_sem_estado_vazio_e_falha(self, monkeypatch):
        monkeypatch.setattr(VagasScraper, "MAX_PAGES", 1)
        monkeypatch.setattr(
            VagasScraper, "_buscar_pagina",
            lambda pagina: "<html><body>Layout inesperado</body></html>"
        )
        monkeypatch.setattr(
            VagasScraper, "_parsear_cards",
            lambda conteudo: ([], 0, 0)
        )

        resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.FAILED
        assert "seletor esperado" in resultado.error

    def test_aceita_href_absoluto(self):
        html = VAGAS_HTML_UMA_VAGA.replace(
            'href="/vaga-engenheiro-de-dados-1234"',
            'href="https://carreiras.example/vagas/1234"',
        )
        resultado = VagasScraper._parsear(html)
        assert resultado[0].link == "https://carreiras.example/vagas/1234"

    def test_parser_remove_cards_com_link_repetido(self):
        resultado = VagasScraper._parsear(VAGAS_HTML_UMA_VAGA + VAGAS_HTML_UMA_VAGA)

        assert len(resultado) == 1


# ════════════════════════════════════════════════════════════════
# TESTES — InfoJobsScraper.coletar (Template Method)
# ════════════════════════════════════════════════════════════════

class TestInfoJobsScraperColetar:

    def test_coleta_vagas_e_conta_pagina(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        monkeypatch.setattr(
            InfoJobsScraper, "_buscar_pagina",
            lambda pagina: INFOJOBS_HTML_MULTIPLAS.encode("utf-8")
        )
        monkeypatch.setattr(
            InfoJobsScraper, "_parsear_cards",
            lambda conteudo: InfoJobsScraper._parsear_detalhado(conteudo)
        )
        monkeypatch.setattr("time.sleep", lambda *_: None)

        resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 2
        assert resultado.pages_processed == 1
        assert resultado.error is None

    def test_html_com_estado_vazio_explicito(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 3)
        monkeypatch.setattr(
            InfoJobsScraper, "_buscar_pagina",
            lambda pagina: '<div class="no-results">Nenhuma vaga encontrada</div>'.encode("utf-8")
        )
        monkeypatch.setattr(
            InfoJobsScraper, "_parsear_cards",
            lambda conteudo: ([], 0, 0)
        )
        monkeypatch.setattr("time.sleep", lambda *_: None)

        resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.EMPTY
        assert resultado.jobs == []
        assert resultado.pages_processed == 1

    def test_html_sem_cards_e_sem_estado_vazio_e_falha(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        monkeypatch.setattr(
            InfoJobsScraper, "_buscar_pagina",
            lambda pagina: INFOJOBS_HTML_VAZIO.encode("utf-8")
        )
        monkeypatch.setattr(
            InfoJobsScraper, "_parsear_cards",
            lambda conteudo: ([], 0, 0)
        )

        resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.FAILED
        assert "seletor esperado" in resultado.error

    def test_falha_de_requisicao_e_reportada(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)

        def buscar_pagina_com_erro(pagina):
            raise requests.exceptions.SSLError("certificado não confiável")

        monkeypatch.setattr(InfoJobsScraper, "_buscar_pagina", buscar_pagina_com_erro)

        resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.FAILED
        assert "SSLError" in resultado.error
        assert resultado.pages_processed == 0

    def test_falha_depois_de_uma_pagina_retorna_parcial(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 2)
        monkeypatch.setattr("time.sleep", lambda *_: None)

        chamadas = [0]
        def buscar_pagina_com_erro_na_segunda(pagina):
            chamadas[0] += 1
            if chamadas[0] == 1:
                return INFOJOBS_HTML_UMA_VAGA.encode("utf-8")
            raise requests.exceptions.Timeout("tempo esgotado")

        monkeypatch.setattr(InfoJobsScraper, "_buscar_pagina", buscar_pagina_com_erro_na_segunda)
        monkeypatch.setattr(
            InfoJobsScraper, "_parsear_cards",
            lambda conteudo: InfoJobsScraper._parsear_detalhado(conteudo)
        )

        resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.PARTIAL
        assert len(resultado.jobs) == 1
        assert resultado.pages_processed == 1
        assert "Timeout" in resultado.error

    def test_paginacao_para_quando_a_pagina_repete_os_mesmos_links(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 3)
        monkeypatch.setattr("time.sleep", lambda *_: None)

        monkeypatch.setattr(
            InfoJobsScraper, "_buscar_pagina",
            lambda pagina: INFOJOBS_HTML_UMA_VAGA.encode("utf-8")
        )
        monkeypatch.setattr(
            InfoJobsScraper, "_parsear_cards",
            lambda conteudo: InfoJobsScraper._parsear_detalhado(conteudo)
        )

        resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 1
        assert resultado.pages_processed == 2


# ════════════════════════════════════════════════════════════════
# TESTES — GupyScraper
# ════════════════════════════════════════════════════════════════

def test_gupy_retorna_scrape_result_e_fecha_browser(monkeypatch):
    vaga = JobSchema(
        titulo="Engenheiro de Dados",
        empresa="Empresa Exemplo",
        link="https://empresa.gupy.io/jobs/123",
        origem="Gupy",
    )
    playwright = MagicMock()
    browser = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = playwright
    context.__exit__.return_value = False
    playwright.chromium.launch.return_value = browser
    monkeypatch.setattr(GupyScraper, "TERMOS_BUSCA", ["engenheiro de dados"])
    monkeypatch.setattr("scrapers.gupy_scraper.sync_playwright", lambda: context)
    monkeypatch.setattr(GupyScraper, "_carregar_pagina", Mock(return_value="html"))
    monkeypatch.setattr(GupyScraper, "_parsear", Mock(return_value=[vaga]))
    monkeypatch.setattr("scrapers.gupy_scraper.time.sleep", lambda _seconds: None)

    resultado = GupyScraper.coletar()

    assert resultado.source == "Gupy"
    assert resultado.status is ScrapeStatus.SUCCESS
    assert resultado.jobs == [vaga]
    assert resultado.pages_processed == 1
    assert GupyScraper.HEADLESS is True
    assert "workplaceTypes" not in GupyScraper.BASE_URL
    browser.close.assert_called_once()


def test_gupy_espera_novas_vagas_com_locator_sem_injetar_javascript(monkeypatch):
    page = MagicMock()
    page.locator.return_value.count.return_value = 2
    page.locator.return_value.nth.return_value.wait_for.return_value = None
    page.content.return_value = "<html></html>"
    monkeypatch.setattr(GupyScraper, "MAX_PAGES", 1)

    html = GupyScraper._carregar_pagina(
        page, "https://portal.gupy.io/job-search/term=data"
    )

    assert html == "<html></html>"
    page.mouse.wheel.assert_called_once_with(0, 2_000)
    page.locator.return_value.nth.assert_called_once_with(2)
    page.evaluate.assert_not_called()
