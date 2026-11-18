"""
Testes unitários para NormalizeService (localização, modalidade, empresa).

Execução: pytest tests/test_normalize.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from services.normalize_service import NormalizeService


# ════════════════════════════════════════════════════════════════
# TESTES DE LOCALIZAÇÃO
# ════════════════════════════════════════════════════════════════

class TestNormalizarLocalizacao:

    def test_formato_cidade_uf(self):
        assert NormalizeService.normalizar_localizacao("São Paulo - SP") == "São Paulo - SP"
        assert NormalizeService.normalizar_localizacao("são paulo - sp") == "São Paulo - SP"

    def test_separador_barra(self):
        assert NormalizeService.normalizar_localizacao("São Paulo/SP") == "São Paulo - SP"
        assert NormalizeService.normalizar_localizacao("Rio de Janeiro/RJ") == "Rio de Janeiro - RJ"

    def test_separador_virgula(self):
        assert NormalizeService.normalizar_localizacao("Campinas, SP") == "Campinas - SP"

    def test_remoto(self):
        assert NormalizeService.normalizar_localizacao("Remoto")        == "Remoto"
        assert NormalizeService.normalizar_localizacao("Home Office")   == "Remoto"
        assert NormalizeService.normalizar_localizacao("home office")   == "Remoto"
        assert NormalizeService.normalizar_localizacao("Trabalho Remoto") == "Remoto"

    def test_hibrido(self):
        assert NormalizeService.normalizar_localizacao("Híbrido")       == "Híbrido"
        assert NormalizeService.normalizar_localizacao("Híbrido - RJ")  == "Híbrido"
        assert NormalizeService.normalizar_localizacao("hibrido")       == "Híbrido"

    def test_vazio_retorna_none(self):
        assert NormalizeService.normalizar_localizacao("")              is None
        assert NormalizeService.normalizar_localizacao(None)            is None
        assert NormalizeService.normalizar_localizacao("Não informado") is None

    def test_placeholder_do_vagas_com_retorna_none(self):
        assert NormalizeService.normalizar_localizacao("Localização não informada") is None

    def test_preposicoes_em_minusculas(self):
        assert NormalizeService.normalizar_localizacao("Franco da Rocha - SP") == "Franco da Rocha - SP"
        assert NormalizeService.normalizar_localizacao("RIO DE JANEIRO / RJ")  == "Rio de Janeiro - RJ"
        assert NormalizeService.normalizar_localizacao("Santa Bárbara d'Oeste - SP") == "Santa Bárbara d'Oeste - SP"

    def test_home_office_com_texto_extra(self):
        assert NormalizeService.normalizar_localizacao("100% Home Office") == "Remoto"

    def test_hifen_no_nome_da_cidade_nao_separa(self):
        assert NormalizeService.normalizar_localizacao("Embu-Guaçu - SP") == "Embu-Guaçu - SP"
        assert NormalizeService.normalizar_localizacao("São Paulo-SP")    == "São Paulo - SP"

    def test_cidade_sem_uf(self):
        assert NormalizeService.normalizar_localizacao("Curitiba") == "Curitiba"


# ════════════════════════════════════════════════════════════════
# TESTES DE MODALIDADE E EMPRESA
# ════════════════════════════════════════════════════════════════

class TestNormalizarModalidade:

    def test_valores_conhecidos(self):
        assert NormalizeService.normalizar_modalidade("Presencial")      == "Presencial"
        assert NormalizeService.normalizar_modalidade("Híbrido")         == "Híbrido"
        assert NormalizeService.normalizar_modalidade("Home Office")     == "Remoto"
        assert NormalizeService.normalizar_modalidade("100% Remoto")     == "Remoto"

    def test_desconhecido_ou_vazio_retorna_none(self):
        assert NormalizeService.normalizar_modalidade("Outra coisa") is None
        assert NormalizeService.normalizar_modalidade(None)          is None
        assert NormalizeService.normalizar_modalidade("")            is None


class TestNormalizarEmpresa:

    def test_remove_espacos_extras(self):
        assert NormalizeService.normalizar_empresa("  Empresa X  ") == "Empresa X"

    def test_confidencial_e_vazio_viram_none(self):
        assert NormalizeService.normalizar_empresa("Confidencial") is None
        assert NormalizeService.normalizar_empresa("")             is None
        assert NormalizeService.normalizar_empresa(None)           is None
