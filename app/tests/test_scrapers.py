"""
Testes unitários para os scrapers (refatoração Sprint 6.5).

Estratégia:
    Testamos apenas o método _parsear() de cada scraper,
    passando HTML fixo que simula o que o portal retornaria.
    Isso evita dependência de rede e torna os testes rápidos e estáveis.

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
from schemas.job_schema import JobSchema


# ═══════════════════════════════════════════════════════════════
# HTML FIXTURES — simulam o que os portais retornam
# ═══════════════════════════════════════════════════════════════

# HTML mínimo que o vagas.com.br retorna por vaga
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

# Vaga sem link — deve ser ignorada
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


# HTML mínimo que o infojobs retorna por vaga
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


# ═══════════════════════════════════════════════════════════════
# TESTES — VagasScraper
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# TESTES — InfoJobsScraper
# ═══════════════════════════════════════════════════════════════

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
        assert resultado[0].localizacao == "Não informado"


def _infojobs_response(html):
    response = Mock()
    response.content = html.encode("utf-8")
    response.raise_for_status.return_value = None
    return response


class TestInfoJobsScraperColetar:
    def test_coleta_vagas_e_conta_pagina(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            return_value=_infojobs_response(INFOJOBS_HTML_MULTIPLAS),
        ):
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 2
        assert resultado.pages_processed == 1
        assert resultado.error is None

    def test_html_com_estado_vazio_explicito(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 3)
        response = _infojobs_response(
            '<div class="no-results">Nenhuma vaga encontrada</div>'
        )
        with patch("scrapers.infojobs_scraper.requests.get", return_value=response) as get:
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.EMPTY
        assert resultado.jobs == []
        assert resultado.pages_processed == 1
        get.assert_called_once()

    def test_html_sem_cards_e_sem_estado_vazio_e_falha(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            return_value=_infojobs_response(INFOJOBS_HTML_VAZIO),
        ):
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.FAILED
        assert "seletor esperado" in resultado.error

    def test_falha_de_requisicao_e_reportada(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            side_effect=requests.exceptions.SSLError("certificado não confiável"),
        ):
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.FAILED
        assert "SSLError" in resultado.error
        assert resultado.pages_processed == 0

    def test_falha_depois_de_uma_pagina_retorna_parcial(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 2)
        monkeypatch.setattr("scrapers.infojobs_scraper.time.sleep", lambda *_: None)
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            side_effect=[
                _infojobs_response(INFOJOBS_HTML_UMA_VAGA),
                requests.exceptions.Timeout("tempo esgotado"),
            ],
        ):
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.PARTIAL
        assert len(resultado.jobs) == 1
        assert resultado.pages_processed == 1
        assert "Timeout" in resultado.error

    def test_usa_bundle_ca_configurado_sem_desativar_tls(self, monkeypatch):
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", "C:/certs/proxy-ca.pem")
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            return_value=_infojobs_response(INFOJOBS_HTML_UMA_VAGA),
        ) as get:
            InfoJobsScraper.coletar()

        assert get.call_args.kwargs["verify"] == "C:/certs/proxy-ca.pem"


def _mock_vagas_browser(html, *, wait_error=None):
    playwright = MagicMock()
    browser = MagicMock()
    page = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = playwright
    context.__exit__.return_value = False
    playwright.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value = SimpleNamespace(status=200)
    page.wait_for_selector.side_effect = wait_error
    page.locator.return_value.count.side_effect = [1, 1]
    page.wait_for_function.side_effect = PlaywrightTimeout("sem novos cards")
    page.content.return_value = html
    return context, browser, page


class TestVagasScraperColetar:
    def test_aguarda_dom_e_retorna_resultado_estruturado(self, monkeypatch):
        monkeypatch.setattr(VagasScraper, "MAX_PAGES", 1)
        context, browser, page = _mock_vagas_browser(VAGAS_HTML_UMA_VAGA)
        with patch("scrapers.vagas_scraper.sync_playwright", return_value=context):
            resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 1
        assert resultado.pages_processed == 1
        page.goto.assert_called_once_with(
            VagasScraper.URL,
            timeout=VagasScraper.NAVIGATION_TIMEOUT_MS,
            wait_until="domcontentloaded",
        )
        browser.close.assert_called_once()

    def test_timeout_com_marcador_de_vazio_retorna_empty(self):
        html = "<p>Nenhuma vaga encontrada nesta busca</p>"
        context, _, _ = _mock_vagas_browser(
            html, wait_error=PlaywrightTimeout("sem cards")
        )
        with patch("scrapers.vagas_scraper.sync_playwright", return_value=context):
            resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.EMPTY
        assert resultado.pages_processed == 1

    def test_timeout_sem_cards_ou_estado_vazio_e_falha(self):
        context, _, _ = _mock_vagas_browser(
            "<html><body>Layout inesperado</body></html>",
            wait_error=PlaywrightTimeout("sem cards"),
        )
        with patch("scrapers.vagas_scraper.sync_playwright", return_value=context):
            resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.FAILED
        assert "Nenhum card" in resultado.error

    def test_aceita_href_absoluto(self):
        html = VAGAS_HTML_UMA_VAGA.replace(
            'href="/vaga-engenheiro-de-dados-1234"',
            'href="https://carreiras.example/vagas/1234"',
        )
        resultado = VagasScraper._parsear(html)
        assert resultado[0].link == "https://carreiras.example/vagas/1234"
