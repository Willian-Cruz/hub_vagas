"""Parser da Catho contra HTML real (20 cards capturados em 11/11/2026) e utilitários de parsing.

Os valores esperados foram conferidos à mão no HTML. Se o portal mudar o layout, salve cards
novos em tests/fixtures/ e ajuste os valores daqui.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.scrapers import catho_parser
from app.scrapers.parser_utils import empresa_ou_none, limpar, parse_salario, salario_sem_beneficios

FIXTURES = Path(__file__).parent / "fixtures"
HOJE = date(2026, 11, 11)  # dia da captura (window.offersgriddata.toddat, na Catho)

CAMPOS_JOBSCHEMA = {
    "titulo", "link", "origem", "empresa", "senioridade", "localizacao", "descricao", "salario",
    "id_externo", "data_publicacao", "modalidade", "experiencia", "escolaridade", "qtd_posicoes",
    "raw_payload",
}


def _ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def catho() -> dict:
    cards = catho_parser.parse_cards(_ler("catho_cards_2026_11.html"), hoje=HOJE)
    return {c.job["id_externo"]: c for c in cards}


# ---------------------------------------------------------------- utilitários


@pytest.mark.parametrize(
    "texto, tipo, minimo, maximo, beneficios",
    [
        ("R$ 4.000,00 a R$ 4.900,00", "faixa", 4000.0, 4900.0, None),
        ("R$ 3.675 + 2 benefícios", "fixo", 3675.0, 3675.0, 2),
        ("R$ 9.726 + 1 benefício", "fixo", 9726.0, 9726.0, 1),
        ("R$ 900 + 3 benefícios", "fixo", 900.0, 900.0, 3),
        ("A partir de R$ 3.000,00", "a_partir", 3000.0, None, None),
        ("Até R$ 2.000,00", "ate", None, 2000.0, None),
        ("A Combinar + 3 benefícios", "a_combinar", None, None, 3),
        ("A combinar", "a_combinar", None, None, None),
        (None, None, None, None, None),
        ("texto sem salário", None, None, None, None),
    ],
)
def test_parse_salario(texto, tipo, minimo, maximo, beneficios):
    assert parse_salario(texto) == {"tipo": tipo, "min": minimo, "max": maximo, "beneficios_qtd": beneficios}


def test_salario_sem_beneficios():
    assert salario_sem_beneficios("R$ 3.675 + 2 benefícios") == "R$ 3.675"
    assert salario_sem_beneficios("A Combinar + 3 benefícios") == "A Combinar"
    assert salario_sem_beneficios("R$ 5.000") == "R$ 5.000"
    assert salario_sem_beneficios(None) is None


def test_empresa_confidencial_vira_none():
    assert empresa_ou_none("Empresa Confidencial") is None
    assert empresa_ou_none("Empresa confidencial") is None
    assert empresa_ou_none("  ") is None
    assert empresa_ou_none("Confidencial Seguros S.A.") == "Confidencial Seguros S.A."


@pytest.mark.parametrize(
    "texto, hoje, esperado",
    [
        ("Publicada Hoje", date(2026, 11, 11), ("publicada", date(2026, 11, 11))),
        ("Publicada Ontem", date(2026, 11, 11), ("publicada", date(2026, 11, 10))),
        ("Atualizada Hoje", date(2026, 11, 11), ("atualizada", date(2026, 11, 11))),
        ("Publicada em 26/10", date(2026, 11, 11), ("publicada", date(2026, 10, 26))),
        ("Publicada em 30/12", date(2026, 1, 5), ("publicada", date(2025, 12, 30))),  # virada de ano
        ("Publicada em 05/01", date(2026, 1, 5), ("publicada", date(2026, 1, 5))),
        ("texto qualquer", date(2026, 11, 11), (None, None)),
        (None, date(2026, 11, 11), (None, None)),
    ],
)
def test_parse_data_card(texto, hoje, esperado):
    assert catho_parser.parse_data_card(texto, hoje) == esperado


# ---------------------------------------------------------------------- Catho


def test_catho_le_os_20_cards(catho):
    assert len(catho) == 20


def test_catho_respeita_o_contrato_do_jobschema(catho):
    for card in catho.values():
        assert set(card.job) == CAMPOS_JOBSCHEMA
        assert card.job["origem"] == "Catho"
        assert card.job["link"].startswith("https://www.catho.com.br/vagas/")
        assert card.job["link"].endswith("/" + card.job["id_externo"])
        assert "html_fragment" in card.job["raw_payload"]
        # o card da Catho não tem estes campos: devem ficar NULL, nunca texto inventado
        for campo in ("descricao", "modalidade", "experiencia", "escolaridade"):
            assert card.job[campo] is None


def test_catho_localizacao_nao_traz_a_quantidade_de_vagas(catho):
    job = catho["39007304"].job
    assert job["localizacao"] == "Piracicaba"
    assert job["qtd_posicoes"] == 5
    assert catho["39232461"].job["localizacao"] == "São Paulo"
    assert catho["39232461"].job["qtd_posicoes"] == 1
    assert all("vaga" not in (c.job["localizacao"] or "").lower() for c in catho.values())


def test_catho_empresa_confidencial_vira_none_sem_o_botao_por_que(catho):
    assert catho["39217274"].job["empresa"] is None
    assert catho["39194258"].job["empresa"] is None
    assert catho["39194569"].job["empresa"] is None
    assert catho["39232461"].job["empresa"] == "RANDSTAD SP"
    assert all("Por que" not in (c.job["empresa"] or "") for c in catho.values())


def test_catho_salario_separa_os_beneficios(catho):
    card = catho["39229049"]
    assert card.job["salario"] == "R$ 3.675"
    assert card.extra["beneficios_qtd"] == 2
    assert (card.extra["salario_tipo"], card.extra["salario_min"], card.extra["salario_max"]) == ("fixo", 3675.0, 3675.0)
    assert catho["39225663"].job["salario"] == "A Combinar"
    assert catho["39225663"].extra["beneficios_qtd"] == 3
    assert all("benef" not in (c.job["salario"] or "").lower() for c in catho.values())


def test_catho_salario_a_partir_de_e_ate(catho):
    a_partir = catho["39214464"]
    assert a_partir.job["salario"] == "A partir de R$ 3.000,00"
    assert (a_partir.extra["salario_tipo"], a_partir.extra["salario_min"], a_partir.extra["salario_max"]) == ("a_partir", 3000.0, None)
    ate = catho["39217274"]
    assert (ate.extra["salario_tipo"], ate.extra["salario_min"], ate.extra["salario_max"]) == ("ate", None, 2000.0)


def test_catho_data_vem_do_texto_e_nao_da_classe_css(catho):
    # "Publicada em 09/11" vem com a classe pub_ontem; a data certa é 09/11, não "ontem" (10/11)
    assert catho["39191473"].job["data_publicacao"] == datetime(2026, 11, 9)
    assert catho["39007304"].job["data_publicacao"] == datetime(2026, 10, 26)
    assert catho["39232461"].job["data_publicacao"] == datetime(2026, 11, 11)  # Publicada Hoje
    assert catho["39214464"].job["data_publicacao"] == datetime(2026, 11, 10)  # Publicada Ontem


def test_catho_atualizada_nao_e_data_de_publicacao(catho):
    for id_, dia in (("39213405", datetime(2026, 11, 11)), ("39194258", datetime(2026, 11, 10))):
        assert catho[id_].job["data_publicacao"] is None
        assert catho[id_].extra["data_atualizacao"] == dia


def test_catho_senioridade_vem_so_do_titulo(catho):
    # Senioridade agora é computada no dbt (Silver), não no parser.
    for card in catho.values():
        assert card.job["senioridade"] is None
        assert card.extra["senioridade_origem"] is None


# ----------------------------------------------- nenhum texto inventado


@pytest.mark.parametrize("campo", ["titulo", "empresa", "localizacao", "descricao", "escolaridade", "modalidade", "experiencia"])
def test_catho_textos_extraidos_existem_no_card(catho, campo):
    for card in catho.values():
        valor = card.job[campo]
        if valor is None:
            continue
        texto_card = limpar(BeautifulSoup(card.job["raw_payload"]["html_fragment"], "html.parser").get_text())
        assert valor in texto_card, (card.job["id_externo"], campo, valor)
