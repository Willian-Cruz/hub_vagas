import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
import pandas as pd
from unittest.mock import patch
from services.export_service import ExportService


# ── DataFrame que simula a resposta do banco ─────────────────────────────────

VAGAS_DF = pd.DataFrame({
    "id": [1, 2],
    "titulo": ["Analista de Dados Jr", "Engenheiro de Dados Jr"],
    "empresa": ["Empresa A", "Empresa B"],
    "senioridade": ["Júnior", "Júnior"],
    "localizacao": ["São Paulo - SP", "Remoto"],
    "salario": ["A combinar", "Não informado"],
    "origem": ["Vagas.com", "InfoJobs"],
    "link": ["https://exemplo.com/1", "https://exemplo.com/2"],
    "descricao": ["Descrição 1", "Descrição 2"],
    "tecnologias": ["python, sql", "python, airflow, sql"],
})


def mock_query(resposta: pd.DataFrame):
    """Patch do método _query_vagas, igual ao padrão usado no AnalyticsService."""
    return patch.object(ExportService, "_query_vagas", return_value=resposta)


# ═══════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════

class TestExportar:

    def test_retorna_caminho_do_arquivo(self, tmp_path):
        with mock_query(VAGAS_DF):
            with patch.object(ExportService, "OUTPUT_DIR", str(tmp_path)):
                caminho = ExportService.exportar("teste.xlsx")

        assert caminho == os.path.join(str(tmp_path), "teste.xlsx")

    def test_arquivo_e_criado_no_disco(self, tmp_path):
        with mock_query(VAGAS_DF):
            with patch.object(ExportService, "OUTPUT_DIR", str(tmp_path)):
                caminho = ExportService.exportar("teste.xlsx")

        assert os.path.exists(caminho)

    def test_conteudo_do_excel_bate_com_o_dataframe(self, tmp_path):
        with mock_query(VAGAS_DF):
            with patch.object(ExportService, "OUTPUT_DIR", str(tmp_path)):
                caminho = ExportService.exportar("teste.xlsx")

        df_lido = pd.read_excel(caminho, sheet_name="vagas")

        assert len(df_lido) == 2
        assert list(df_lido["titulo"]) == [
            "Analista de Dados Jr",
            "Engenheiro de Dados Jr",
        ]
        assert "tecnologias" in df_lido.columns

    def test_cria_diretorio_se_nao_existir(self, tmp_path):
        novo_dir = os.path.join(str(tmp_path), "pasta_nova")

        with mock_query(VAGAS_DF):
            with patch.object(ExportService, "OUTPUT_DIR", novo_dir):
                ExportService.exportar("teste.xlsx")

        assert os.path.isdir(novo_dir)

    def test_usa_nome_padrao_quando_nao_informado(self, tmp_path):
        with mock_query(VAGAS_DF):
            with patch.object(ExportService, "OUTPUT_DIR", str(tmp_path)):
                caminho = ExportService.exportar()

        assert caminho.endswith("vagas.xlsx")
