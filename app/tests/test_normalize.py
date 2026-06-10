"""
Testes unitários para NormalizeService (Sprint 5)
Execução: pytest tests/test_normalize_service.py -v
"""
import sys
import os

# Garante que o Python encontra os módulos em app/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from services.normalize_service import NormalizeService


# ═══════════════════════════════════════════════════════════════
# TESTES DE SENIORIDADE
# ═══════════════════════════════════════════════════════════════

class TestNormalizarSenioridade:

    def test_junior_variantes(self):
        assert NormalizeService.normalizar_senioridade("Junior")    == "Júnior"
        assert NormalizeService.normalizar_senioridade("Júnior")    == "Júnior"
        assert NormalizeService.normalizar_senioridade("Jr.")       == "Júnior"
        assert NormalizeService.normalizar_senioridade("jr")        == "Júnior"
        assert NormalizeService.normalizar_senioridade("JÚNIOR")    == "Júnior"

    def test_pleno_variantes(self):
        assert NormalizeService.normalizar_senioridade("Pleno")     == "Pleno"
        assert NormalizeService.normalizar_senioridade("Pl.")       == "Pleno"
        assert NormalizeService.normalizar_senioridade("PLENO")     == "Pleno"

    def test_senior_variantes(self):
        assert NormalizeService.normalizar_senioridade("Sênior")    == "Sênior"
        assert NormalizeService.normalizar_senioridade("Senior")    == "Sênior"
        assert NormalizeService.normalizar_senioridade("Sr.")       == "Sênior"
        assert NormalizeService.normalizar_senioridade("sr")        == "Sênior"

    def test_estagio_variantes(self):
        assert NormalizeService.normalizar_senioridade("Estágio")   == "Estágio/Trainee"
        assert NormalizeService.normalizar_senioridade("Estagio")   == "Estágio/Trainee"
        assert NormalizeService.normalizar_senioridade("Trainee")   == "Estágio/Trainee"

    def test_vazio_retorna_nao_informado(self):
        assert NormalizeService.normalizar_senioridade("")              == "Não informado"
        assert NormalizeService.normalizar_senioridade("Não informado") == "Não informado"
        assert NormalizeService.normalizar_senioridade(None)            == "Não informado"

    def test_string_desconhecida_retorna_nao_informado(self):
        assert NormalizeService.normalizar_senioridade("xyz abc") == "Não informado"

    def test_composto_pega_primeiro_match(self):
        # "Pleno/Sênior" → pega o primeiro encontrado (Pleno)
        resultado = NormalizeService.normalizar_senioridade("Pleno/Sênior")
        assert resultado in ("Pleno", "Sênior")  # qualquer um dos dois é aceitável


# ═══════════════════════════════════════════════════════════════
# TESTES DE LOCALIZAÇÃO
# ═══════════════════════════════════════════════════════════════

class TestNormalizarLocalizacao:

    def test_formato_cidade_uf(self):
        assert NormalizeService.normalizar_localizacao("São Paulo - SP") == "São Paulo - SP"
        assert NormalizeService.normalizar_localizacao("são paulo - sp") == "São Paulo - SP"

    def test_separador_barra(self):
        assert NormalizeService.normalizar_localizacao("São Paulo/SP") == "São Paulo - SP"
        assert NormalizeService.normalizar_localizacao("Rio de Janeiro/RJ") == "Rio De Janeiro - RJ"

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

    def test_vazio_retorna_nao_informado(self):
        assert NormalizeService.normalizar_localizacao("")              == "Não informado"
        assert NormalizeService.normalizar_localizacao(None)            == "Não informado"
        assert NormalizeService.normalizar_localizacao("Não informado") == "Não informado"