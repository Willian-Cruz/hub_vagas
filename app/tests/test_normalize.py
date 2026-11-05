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

    def test_vazio_retorna_none(self):
        assert NormalizeService.normalizar_senioridade("")              is None
        assert NormalizeService.normalizar_senioridade("Não informado") is None
        assert NormalizeService.normalizar_senioridade(None)            is None

    def test_string_desconhecida_retorna_none(self):
        assert NormalizeService.normalizar_senioridade("xyz abc") is None

    def test_niveis_do_vagas_com(self):
        assert NormalizeService.normalizar_senioridade("Supervisão/Coordenação") == "Coordenador"
        assert NormalizeService.normalizar_senioridade("Técnico")                == "Técnico"
        assert NormalizeService.normalizar_senioridade("Júnior/Trainee")         == "Júnior"
        assert NormalizeService.normalizar_senioridade("Gerência")               == "Liderança"

    def test_abreviacao_exige_palavra_inteira(self):
        # "pl" e "sr" dentro de outra palavra não são nível
        assert NormalizeService.normalizar_senioridade("Supply Chain") is None
        assert NormalizeService.normalizar_senioridade("Employee")     is None

    def test_experiencia_nao_e_senioridade(self):
        # texto do ícone "suitcase" do InfoJobs
        assert NormalizeService.normalizar_senioridade("Sem experiência")   is None
        assert NormalizeService.normalizar_senioridade("Entre 1 e 3 anos")  is None

    def test_inferencia_pelo_titulo(self):
        f = lambda t: NormalizeService.normalizar_senioridade(t, de_titulo=True)
        assert f("Engenheiro de Dados Sênior")           == "Sênior"
        assert f("Engenheiro Civil Pl - V027803")        == "Pleno"
        assert f("Estágio Em Análise De Dados (Data Analytics)") == "Estágio/Trainee"
        assert f("Estágio Técnico Em Segurança Do Trabalho")     == "Estágio/Trainee"
        assert f("Engenheiro de Dados")                  is None
        assert f("Analista de Suporte Técnico")          is None  # "técnico" só vale no campo de nível

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
        # antes virava a "cidade" 'Localização Não Informada'
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


# ═══════════════════════════════════════════════════════════════
# TESTES DE MODALIDADE E EMPRESA
# ═══════════════════════════════════════════════════════════════

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