import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
 
import pytest
import pandas as pd
from unittest.mock import patch
from services.analytics_service import AnalyticsService
 
 
# ── DataFrames que simulam respostas do banco ────────────────────────────────
 
SENIORIDADE_DF = pd.DataFrame({
    "label": ["Pleno", "Sênior", "Júnior"],
    "total": [30, 25, 15],
})
 
LOCALIZACAO_DF = pd.DataFrame({
    "label": ["São Paulo - SP", "Rio de Janeiro - RJ", "Curitiba - PR"],
    "total": [40, 20, 10],
})
 
MODALIDADE_DF = pd.DataFrame({
    "label": ["Presencial", "Remoto", "Híbrido"],
    "total": [50, 30, 20],
})
 
TECNOLOGIAS_DF = pd.DataFrame({
    "label": ["python", "sql", "aws"],
    "total": [60, 45, 30],
})
 
ORIGEM_DF = pd.DataFrame({
    "label": ["Vagas.com", "InfoJobs"],
    "total": [40, 20],
})
 
SALARIOS_DF = pd.DataFrame({
    "label": ["Não informado", "A combinar", "Salário informado"],
    "total": [45, 30, 25],
})
 
RESUMO_DF = pd.DataFrame({
    "total_vagas":    [60],
    "total_empresas": [35],
    "total_portais":  [2],
})
 
TECH_COUNT_DF = pd.DataFrame({"total": [18]})
 
 
# ── Helper: substitui _query retornando DFs em sequência ────────────────────
 
def mock_query(respostas: list):
    """Patch do método _query com side_effect para múltiplas chamadas."""
    return patch.object(AnalyticsService, "_query", side_effect=respostas)
 
 
# ═══════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════
 
class TestVagasPorSenioridade:
 
    def test_retorna_dataframe(self):
        with mock_query([SENIORIDADE_DF]):
            df = AnalyticsService.vagas_por_senioridade()
        assert isinstance(df, pd.DataFrame)
 
    def test_colunas_corretas(self):
        with mock_query([SENIORIDADE_DF]):
            df = AnalyticsService.vagas_por_senioridade()
        assert "label" in df.columns
        assert "total" in df.columns
 
    def test_valores_corretos(self):
        with mock_query([SENIORIDADE_DF]):
            df = AnalyticsService.vagas_por_senioridade()
        assert df.iloc[0]["label"] == "Pleno"
        assert df.iloc[0]["total"] == 30
 
 
class TestVagasPorLocalizacao:
 
    def test_retorna_dataframe(self):
        with mock_query([LOCALIZACAO_DF]):
            df = AnalyticsService.vagas_por_localizacao()
        assert isinstance(df, pd.DataFrame)
 
    def test_aceita_parametro_top_n(self):
        with mock_query([LOCALIZACAO_DF]):
            df = AnalyticsService.vagas_por_localizacao(top_n=5)
        assert isinstance(df, pd.DataFrame)
 
    def test_colunas_corretas(self):
        with mock_query([LOCALIZACAO_DF]):
            df = AnalyticsService.vagas_por_localizacao()
        assert "label" in df.columns
        assert "total" in df.columns
 
 
class TestVagasPorModalidade:
 
    def test_retorna_dataframe(self):
        with mock_query([MODALIDADE_DF]):
            df = AnalyticsService.vagas_por_modalidade()
        assert isinstance(df, pd.DataFrame)
 
    def test_contem_modalidades_esperadas(self):
        with mock_query([MODALIDADE_DF]):
            df = AnalyticsService.vagas_por_modalidade()
        labels = df["label"].tolist()
        assert "Presencial" in labels
        assert "Remoto"     in labels
        assert "Híbrido"    in labels
 
 
class TestTopTecnologias:
 
    def test_retorna_dataframe(self):
        with mock_query([TECNOLOGIAS_DF]):
            df = AnalyticsService.top_tecnologias()
        assert isinstance(df, pd.DataFrame)
 
    def test_python_esta_presente(self):
        with mock_query([TECNOLOGIAS_DF]):
            df = AnalyticsService.top_tecnologias()
        assert "python" in df["label"].values
 
    def test_aceita_parametro_top_n(self):
        with mock_query([TECNOLOGIAS_DF]):
            df = AnalyticsService.top_tecnologias(top_n=5)
        assert isinstance(df, pd.DataFrame)
 
    def test_colunas_corretas(self):
        with mock_query([TECNOLOGIAS_DF]):
            df = AnalyticsService.top_tecnologias()
        assert "label" in df.columns
        assert "total" in df.columns
 
 
class TestVagasPorOrigem:
 
    def test_retorna_dataframe(self):
        with mock_query([ORIGEM_DF]):
            df = AnalyticsService.vagas_por_origem()
        assert isinstance(df, pd.DataFrame)
 
    def test_portais_presentes(self):
        with mock_query([ORIGEM_DF]):
            df = AnalyticsService.vagas_por_origem()
        assert "Vagas.com" in df["label"].values
        assert "InfoJobs"  in df["label"].values
 
    def test_colunas_corretas(self):
        with mock_query([ORIGEM_DF]):
            df = AnalyticsService.vagas_por_origem()
        assert "label" in df.columns
        assert "total" in df.columns
 
 
class TestDistribuicaoSalarios:
 
    def test_retorna_dataframe(self):
        with mock_query([SALARIOS_DF]):
            df = AnalyticsService.distribuicao_salarios()
        assert isinstance(df, pd.DataFrame)
 
    def test_contem_nao_informado(self):
        with mock_query([SALARIOS_DF]):
            df = AnalyticsService.distribuicao_salarios()
        assert "Não informado" in df["label"].values
 
    def test_contem_a_combinar(self):
        with mock_query([SALARIOS_DF]):
            df = AnalyticsService.distribuicao_salarios()
        assert "A combinar" in df["label"].values
 
    def test_contem_salario_informado(self):
        with mock_query([SALARIOS_DF]):
            df = AnalyticsService.distribuicao_salarios()
        assert "Salário informado" in df["label"].values
 
 
class TestResumoGeral:
 
    def test_retorna_dict(self):
        with mock_query([RESUMO_DF, TECH_COUNT_DF]):
            resultado = AnalyticsService.resumo_geral()
        assert isinstance(resultado, dict)
 
    def test_chaves_presentes(self):
        with mock_query([RESUMO_DF, TECH_COUNT_DF]):
            resultado = AnalyticsService.resumo_geral()
        assert "total_vagas"    in resultado
        assert "total_empresas" in resultado
        assert "total_portais"  in resultado
        assert "total_techs"    in resultado
 
    def test_valores_corretos(self):
        with mock_query([RESUMO_DF, TECH_COUNT_DF]):
            resultado = AnalyticsService.resumo_geral()
        assert resultado["total_vagas"]    == 60
        assert resultado["total_empresas"] == 35
        assert resultado["total_portais"]  == 2
        assert resultado["total_techs"]    == 18
 
    def test_tipos_sao_int(self):
        with mock_query([RESUMO_DF, TECH_COUNT_DF]):
            resultado = AnalyticsService.resumo_geral()
        # Garante que os valores são int Python, não numpy.int64
        for chave, valor in resultado.items():
            assert isinstance(valor, int), f"{chave} deveria ser int, mas é {type(valor)}"
