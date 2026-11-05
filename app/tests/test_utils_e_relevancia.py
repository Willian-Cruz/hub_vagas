"""
Testes dos utilitários de texto/data e do filtro de relevância.

Execução: pytest tests/test_utils_e_relevancia.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime

import pytest

from services.relevance_service import RelevanceService
from utils.date_utils import parse_data_infojobs, parse_data_vagas
from utils.text_utils import chave_conteudo, valor_ou_none

REFERENCIA = date(2026, 11, 3)


class TestValorOuNone:

    @pytest.mark.parametrize(
        "texto",
        [None, "", "   ", "Confidencial", "confidencial", "Localização não informada",
         "Localização Não Informada", "Não informado", "nao informado", "-"],
    )
    def test_placeholders_viram_none(self, texto):
        assert valor_ou_none(texto) is None

    def test_texto_valido_e_limpo(self):
        assert valor_ou_none("  São   Paulo \n SP ") == "São Paulo SP"


class TestChaveConteudo:

    def test_ignora_acentos_caixa_e_espacos(self):
        a = chave_conteudo("Vagas.com", "Engenheiro  Civil Pl - V027803", "Lyon Engenharia", "Guarujá - SP")
        b = chave_conteudo("Vagas.com", "engenheiro civil pl - v027803", "LYON ENGENHARIA", "Guaruja - SP")
        assert a == b == "vagas.com|engenheiro civil pl - v027803|lyon engenharia|guaruja - sp"

    def test_none_sem_empresa_ou_local(self):
        # sem eles, duas vagas diferentes com o mesmo título seriam juntadas
        assert chave_conteudo("Vagas.com", "Executivo de Vendas", None, "São Paulo - SP") is None
        assert chave_conteudo("Vagas.com", "Executivo de Vendas", "Atex", None) is None

    def test_origem_diferente_gera_chave_diferente(self):
        a = chave_conteudo("Vagas.com", "Analista de Dados", "Empresa", "São Paulo - SP")
        b = chave_conteudo("InfoJobs", "Analista de Dados", "Empresa", "São Paulo - SP")
        assert a != b


class TestDataVagas:

    def test_ha_n_dias(self):
        assert parse_data_vagas("Há 4 dias", REFERENCIA) == datetime(2026, 10, 30)
        assert parse_data_vagas("Há 1 dia", REFERENCIA) == datetime(2026, 11, 2)

    def test_data_absoluta(self):
        assert parse_data_vagas("21/10/2026", REFERENCIA) == datetime(2026, 10, 21)

    def test_horas_hoje_e_ontem(self):
        assert parse_data_vagas("Há 3 horas", REFERENCIA) == datetime(2026, 11, 3)
        assert parse_data_vagas("Hoje", REFERENCIA) == datetime(2026, 11, 3)
        assert parse_data_vagas("Ontem", REFERENCIA) == datetime(2026, 11, 2)

    def test_formato_desconhecido_ou_invalido_vira_none(self):
        assert parse_data_vagas("em breve", REFERENCIA) is None
        assert parse_data_vagas("31/02/2026", REFERENCIA) is None
        assert parse_data_vagas("", REFERENCIA) is None
        assert parse_data_vagas(None, REFERENCIA) is None


class TestDataInfoJobs:

    def test_data_e_hora(self):
        assert parse_data_infojobs("2026/10/30 10:59:00") == datetime(2026, 10, 30, 10, 59, 0)

    def test_so_data(self):
        assert parse_data_infojobs("2026/10/30") == datetime(2026, 10, 30)

    def test_invalido_vira_none(self):
        assert parse_data_infojobs("") is None
        assert parse_data_infojobs(None) is None
        assert parse_data_infojobs("30 out") is None


class TestRelevancia:

    @pytest.mark.parametrize(
        "titulo",
        [
            "Engenheiro de Dados Sênior",
            "Data Engineer",
            "Analista BI",
            "Cientista de Dados",
            "Analytics Engineer",
            "Analista de Business Intelligence",
            "Especialista em Inteligência Artificial",
            "Estágio em Eng. de Produção, Eng. de Software, Banco de Dados",
            "Desenvolvedor Python",
            "DBA Oracle",
        ],
    )
    def test_titulos_de_dados_passam(self, titulo):
        assert RelevanceService.eh_relevante(titulo) is True

    @pytest.mark.parametrize(
        "titulo",
        [
            "Engenheiro Civil Pl - V027803",
            "Executivo de Vendas",
            "Estágio em Engenharia Elétrica",
            "Engenheiro de Segurança do Trabalho Pleno",
            "Analista de Inteligência de Mercado",
            "Abitibi Operador",
            "",
            None,
        ],
    )
    def test_titulos_fora_do_tema_sao_descartados(self, titulo):
        assert RelevanceService.eh_relevante(titulo) is False

    def test_termo_so_vale_como_palavra_inteira(self):
        # "bi" dentro de "Abitibi" e "ia" dentro de "Pia" não contam
        assert RelevanceService.eh_relevante("Pia de Cozinha") is False
