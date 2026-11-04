import os
import pandas as pd
from sqlalchemy import text
from database.connection import engine
from utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """
    Exporta os dados prontos para consumo do mart `gold.mart_vagas`.

    Esse arquivo é o ponto de entrada do tratamento manual: depois
    de gerado, ele é aberto e ajustado no Excel, e o resultado final
    alimenta o dashboard no Power BI.
    """

    OUTPUT_DIR = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "exports"
    )

    # ─────────────────────────────────────────────────────────────
    # QUERY
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _query_vagas() -> pd.DataFrame:
        """
        Busca o mart Gold de vagas, já com as tecnologias agregadas.
        """
        sql = """
            SELECT
                id,
                titulo,
                empresa,
                senioridade,
                localizacao,
                salario,
                origem,
                link,
                descricao,
                data_coleta,
                tecnologias
            FROM gold.mart_vagas
            ORDER BY id
        """
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)

    # ─────────────────────────────────────────────────────────────
    # EXPORTAÇÃO
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def exportar(cls, nome_arquivo: str = "vagas.xlsx") -> str:
        """
        Gera o Excel com todas as vagas coletadas.

        Retorna o caminho absoluto do arquivo gerado.
        """
        df = cls._query_vagas()

        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        caminho = os.path.join(cls.OUTPUT_DIR, nome_arquivo)

        df.to_excel(caminho, index=False, sheet_name="vagas")

        logger.info(f"Exportado: {len(df)} vaga(s) -> {caminho}")
        return caminho
