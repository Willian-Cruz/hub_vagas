"""
Testes dos parsers contra HTML REAL dos portais.

As fixtures em tests/fixtures são os cards de verdade (Vagas.com: 28 cards da
busca "engenheiro de dados"; InfoJobs: 9 cards da página 1), coletados em
2026-11-03. Os testes com HTML escrito à mão (test_scrapers.py) não pegam
seletor que não bate com o portal; estes pegam.

Para atualizar as fixtures quando um portal mudar o layout, salve o HTML novo
e extraia só os cards (li.vaga / div.js_vacancyLoad).

Execução: pytest tests/test_parsers_html_real.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from scrapers.base_scraper import ScrapeStatus
from scrapers.infojobs_scraper import InfoJobsScraper
from scrapers.vagas_scraper import VagasScraper
from services.relevance_service import RelevanceService

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCIA = date(2026, 11, 3)  # dia da coleta das fixtures


@pytest.fixture(scope="module")
def vagas_html():
    return (FIXTURES / "vagas_com_cards.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def vagas(vagas_html):
    jobs, invalidos, cards = VagasScraper._parsear_detalhado(
        vagas_html, referencia=REFERENCIA
    )
    return jobs, invalidos, cards


@pytest.fixture(scope="module")
def infojobs_html():
    return (FIXTURES / "infojobs_cards.html").read_bytes()


@pytest.fixture(scope="module")
def infojobs(infojobs_html):
    return InfoJobsScraper._parsear_detalhado(infojobs_html)


# ═══════════════════════════════════════════════════════════════
# VAGAS.COM — parser
# ═══════════════════════════════════════════════════════════════

class TestVagasComHtmlReal:

    def test_extrai_todos_os_cards(self, vagas):
        jobs, invalidos, cards = vagas
        assert (len(jobs), invalidos, cards) == (28, 0, 28)

    def test_id_externo_vem_do_atributo_e_e_unico(self, vagas):
        jobs, _, _ = vagas
        assert jobs[0].id_externo == "2840818"
        assert all(j.id_externo for j in jobs)
        assert len({j.id_externo for j in jobs}) == 28

    def test_link_absoluto_sem_querystring(self, vagas):
        jobs, _, _ = vagas
        assert jobs[0].link == (
            "https://www.vagas.com.br/vagas/v2840818/engenheiro-de-dados-senior"
        )
        assert all("?" not in j.link for j in jobs)

    def test_titulo_vem_do_atributo_title_sem_espaco_extra(self, vagas):
        # get_text() em volta do <mark> gerava "Engenheiro (a)"
        titulos = [j.titulo for j in vagas[0]]
        assert "Engenheiro(a) Geotécnico(a) - Ato" in titulos
        assert "Engenheiro(a) Civil - Hidráulica e Saneamento" in titulos
        assert not any("Engenheiro (a)" in t for t in titulos)

    def test_empresa_confidencial_vira_none(self, vagas):
        jobs, _, _ = vagas
        assert sum(1 for j in jobs if j.empresa is None) == 5
        assert "Confidencial" not in {j.empresa for j in jobs}
        assert jobs[0].empresa is None

    def test_local_nao_informado_vira_none(self, vagas):
        jobs, _, _ = vagas
        assert sum(1 for j in jobs if j.localizacao is None) == 3
        assert jobs[0].localizacao is None

    def test_local_vem_sem_o_balao_da_empresa(self, vagas):
        locais = [j.localizacao for j in vagas[0]]
        assert locais.count("São Paulo / SP") == 6
        assert not any("A empresa aceita" in (local or "") for local in locais)

    def test_local_em_span_home_office_e_capturado(self, vagas):
        # Este card usa <span class="vaga-local">, não <div>: o scraper antigo
        # não achava e gravava "Não informado".
        job = next(
            j for j in vagas[0] if j.titulo.startswith("Estágio em Eng. de Produção")
        )
        assert job.localizacao == "100% Home Office"

    def test_data_de_publicacao_relativa_e_absoluta(self, vagas):
        jobs, _, _ = vagas
        assert all(j.data_publicacao is not None for j in jobs)
        assert jobs[0].data_publicacao == datetime(2026, 10, 27)  # "Há 7 dias"
        assert datetime(2026, 7, 29) in {j.data_publicacao for j in jobs}  # "29/07/2026"

    def test_quantidade_de_posicoes(self, vagas):
        # "Pleno - 2 vagas" e "Estágio - 2 vagas"
        assert sorted(j.qtd_posicoes for j in vagas[0] if j.qtd_posicoes) == [2, 2]

    def test_senioridade_bruta_do_card(self, vagas):
        assert vagas[0][0].senioridade == "Sênior"

    def test_descricao_sem_espacos_duplicados(self, vagas):
        for job in vagas[0]:
            assert job.descricao
            assert "  " not in job.descricao

    def test_filtro_de_relevancia_mantem_so_vagas_de_dados(self, vagas):
        relevantes, descartadas = RelevanceService.separar(vagas[0])
        titulos_ok = {j.titulo for j in relevantes}
        titulos_fora = {j.titulo for j in descartadas}

        assert (len(relevantes), len(descartadas)) == (6, 22)
        assert "Engenheiro de Dados Sênior" in titulos_ok
        assert "Especialista em Inteligência Artificial" in titulos_ok
        assert "Executivo de Vendas" in titulos_fora
        assert "Engenheiro Civil Pl - V027803" in titulos_fora


# ═══════════════════════════════════════════════════════════════
# INFOJOBS — parser
# ═══════════════════════════════════════════════════════════════

class TestInfoJobsHtmlReal:

    def test_extrai_todos_os_cards(self, infojobs):
        jobs, invalidos, cards = infojobs
        assert (len(jobs), invalidos, cards) == (9, 0, 9)

    def test_primeiro_card_completo(self, infojobs):
        job = infojobs[0][0]
        assert job.titulo == "Estágio Em Segurança Do Trabalho"
        assert job.empresa == "Futura Estágios"
        assert job.id_externo == "11815887"
        assert job.link == (
            "https://www.infojobs.com.br/"
            "vaga-de-estagio-seguranca-do-trabalho-em-rio-grande-do-sul__11815887.aspx"
        )
        assert job.localizacao == "Porto Alegre - RS"
        assert job.salario == "R$ 1.500,00"
        assert job.escolaridade == "Curso Técnico"
        assert job.modalidade == "Presencial"
        assert job.experiencia is None
        assert job.data_publicacao == datetime(2026, 10, 30, 10, 59, 0)
        assert job.descricao.startswith("Auxiliar técnico de segurança no trabalho")

    def test_salario_vem_do_icone_de_dinheiro(self, infojobs):
        assert [j.salario for j in infojobs[0]] == [
            "R$ 1.500,00",
            "A combinar",
            "R$ 1.500,00",
            "R$ 1.500,00",
            "A combinar",
            "R$ 1.800,00",
            "A combinar",
            "R$ 1.000,00 a R$ 1.200,00",
            "R$ 1.000,00",
        ]

    def test_suitcase_e_experiencia_nao_senioridade(self, infojobs):
        jobs, _, _ = infojobs
        assert [j.experiencia for j in jobs] == [
            None,
            "Entre 1 e 3 anos",
            "Sem experiência",
            "Só estágios",
            None,
            None,
            None,
            "Sem experiência",
            None,
        ]
        assert all(j.senioridade is None for j in jobs)

    def test_modalidade_e_escolaridade(self, infojobs):
        jobs, _, _ = infojobs
        assert {j.modalidade for j in jobs} == {"Presencial"}
        assert all(j.escolaridade for j in jobs)

    def test_local_sem_o_texto_oculto_de_distancia(self, infojobs):
        locais = [j.localizacao for j in infojobs[0]]
        assert not any("Km" in local for local in locais)
        assert locais[:3] == ["Porto Alegre - RS", "Novo Hamburgo - RS", "São Paulo - SP"]

    def test_descricao_nao_e_metadado_nem_data(self, infojobs):
        for job in infojobs[0]:
            assert job.descricao and len(job.descricao) > 80
            assert not job.descricao.startswith("R$")

    def test_data_de_publicacao_exata_em_todos(self, infojobs):
        jobs, _, _ = infojobs
        assert all(j.data_publicacao is not None for j in jobs)
        assert jobs[-1].data_publicacao == datetime(2026, 9, 21, 2, 23, 0)

    def test_filtro_de_relevancia_mantem_so_a_vaga_de_dados(self, infojobs):
        relevantes, descartadas = RelevanceService.separar(infojobs[0])
        assert len(relevantes) == 1
        assert relevantes[0].titulo.startswith("Estágio Em Análise De Dados")
        assert len(descartadas) == 8


# ═══════════════════════════════════════════════════════════════
# COLETA — filtro de relevância integrado aos scrapers
# ═══════════════════════════════════════════════════════════════

def _resposta(html: str):
    resposta = Mock()
    resposta.content = html.encode("utf-8")
    resposta.raise_for_status.return_value = None
    return resposta


def _card_infojobs(titulo: str, href: str) -> str:
    return (
        f'<div class="js_vacancyLoad" data-href="{href}">'
        f"<h2>{titulo}</h2>"
        '<div class="d-flex align-items-baseline"><a href="#">Empresa</a></div>'
        '<div class="mb-8">São Paulo - SP</div>'
        '<div class="text-medium">Descrição da vaga.</div>'
        "</div>"
    )


class TestInfoJobsColetaComFiltro:

    def test_pagina_real_devolve_so_a_vaga_de_dados_e_conta_descartadas(
        self, monkeypatch, infojobs_html
    ):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            return_value=_resposta(infojobs_html.decode("utf-8")),
        ):
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 1
        assert resultado.discarded == 8
        assert resultado.error is None

    def test_pagina_so_com_vagas_fora_do_tema_nao_encerra_a_paginacao(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 5)
        monkeypatch.setattr("scrapers.infojobs_scraper.time.sleep", lambda *_: None)
        pagina_1 = _card_infojobs("Executivo de Vendas", "/vaga-x__1.aspx")
        pagina_2 = _card_infojobs("Engenheiro de Dados", "/vaga-y__2.aspx")
        with patch(
            "scrapers.infojobs_scraper.requests.get",
            side_effect=[_resposta(pagina_1), _resposta(pagina_2), _resposta(pagina_2)],
        ) as get:
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert [j.titulo for j in resultado.jobs] == ["Engenheiro de Dados"]
        assert resultado.discarded == 1
        assert get.call_count == 3  # 3ª página repete o link da 2ª e encerra

    def test_so_vagas_fora_do_tema_e_coleta_vazia_sem_erro(self, monkeypatch):
        monkeypatch.setattr(InfoJobsScraper, "MAX_PAGES", 1)
        pagina = _card_infojobs("Executivo de Vendas", "/vaga-x__1.aspx")
        with patch(
            "scrapers.infojobs_scraper.requests.get", return_value=_resposta(pagina)
        ):
            resultado = InfoJobsScraper.coletar()

        assert resultado.status is ScrapeStatus.EMPTY
        assert resultado.jobs == []
        assert resultado.discarded == 1
        assert resultado.error is None


def _mock_vagas_browser(html):
    playwright = MagicMock()
    browser = MagicMock()
    page = MagicMock()
    contexto = MagicMock()
    contexto.__enter__.return_value = playwright
    contexto.__exit__.return_value = False
    playwright.chromium.launch.return_value = browser
    browser.new_page.return_value = page
    page.goto.return_value = SimpleNamespace(status=200)
    page.locator.return_value.count.side_effect = [1, 1]
    page.wait_for_function.side_effect = PlaywrightTimeout("sem novos cards")
    page.content.return_value = html
    return contexto


class TestVagasColetaComFiltro:

    def test_pagina_real_devolve_so_vagas_de_dados_e_conta_descartadas(
        self, monkeypatch, vagas_html
    ):
        monkeypatch.setattr(VagasScraper, "MAX_PAGES", 1)
        with patch(
            "scrapers.vagas_scraper.sync_playwright",
            return_value=_mock_vagas_browser(vagas_html),
        ):
            resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.SUCCESS
        assert len(resultado.jobs) == 6
        assert resultado.discarded == 22
        assert resultado.error is None

    def test_so_vagas_fora_do_tema_e_coleta_vazia_sem_erro(self, monkeypatch):
        monkeypatch.setattr(VagasScraper, "MAX_PAGES", 1)
        html = (
            '<ul><li class="vaga">'
            '<a class="link-detalhes-vaga" href="/vagas/v1/executivo" '
            'title="Executivo de Vendas">Executivo de Vendas</a>'
            "</li></ul>"
        )
        with patch(
            "scrapers.vagas_scraper.sync_playwright",
            return_value=_mock_vagas_browser(html),
        ):
            resultado = VagasScraper.coletar()

        assert resultado.status is ScrapeStatus.EMPTY
        assert resultado.jobs == []
        assert resultado.discarded == 1
        assert resultado.error is None
