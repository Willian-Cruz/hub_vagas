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