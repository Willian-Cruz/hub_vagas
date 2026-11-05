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
    "data_coleta": pd.to_datetime(["2026-06-20 10:00:00", "2026-06-20 10:05:00"]),
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
        assert "data_coleta" in df_lido.columns

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


class TestDatasComFuso:
    """O mart Gold devolve timestamptz; to_excel recusa datas com fuso."""

    def test_exporta_colunas_com_fuso_horario(self, tmp_path):
        df = VAGAS_DF.copy()
        df["data_coleta"] = pd.to_datetime(
            ["2026-06-20 13:00:00", "2026-06-20 13:05:00"], utc=True
        )

        with mock_query(df):
            with patch.object(ExportService, "OUTPUT_DIR", str(tmp_path)):
                caminho = ExportService.exportar("fuso.xlsx")

        lido = pd.read_excel(caminho, sheet_name="vagas")
        # 13:00 UTC = 10:00 em São Paulo
        assert lido["data_coleta"].iloc[0] == pd.Timestamp("2026-06-20 10:00:00")

    def test_nao_altera_o_dataframe_de_quem_chamou_sem_fuso(self, tmp_path):
        with mock_query(VAGAS_DF):
            with patch.object(ExportService, "OUTPUT_DIR", str(tmp_path)):
                ExportService.exportar("sem_fuso.xlsx")

        assert VAGAS_DF["data_coleta"].iloc[0] == pd.Timestamp("2026-06-20 10:00:00")


class TestCamposNovosNoMart:

    def test_consulta_pede_os_campos_novos_do_mart(self):
        capturado = {}

        class _Conn:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def _fake_read_sql(sql, conn):
            capturado["sql"] = str(sql)
            return pd.DataFrame()

        with patch("services.export_service.engine") as engine, \
                patch("services.export_service.pd.read_sql", side_effect=_fake_read_sql):
            engine.connect.return_value = _Conn()
            ExportService._query_vagas()

        for coluna in (
            "id_externo", "data_publicacao", "modalidade",
            "experiencia", "escolaridade", "qtd_posicoes",
        ):
            assert coluna in capturado["sql"]
        assert "gold.mart_vagas" in capturado["sql"]
