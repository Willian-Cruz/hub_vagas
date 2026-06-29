import os
import pandas as pd
from sqlalchemy import text
from database.connection import engine


class ExportService:
    """
    Exporta os dados já normalizados da tabela `jobs` para Excel.

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
        Busca todas as vagas com as tecnologias agregadas em uma
        única coluna (separadas por vírgula), pronta para o Excel.
        """
        sql = """
            SELECT
                j.id,
                j.titulo,
                j.empresa,
                j.senioridade,
                j.localizacao,
                j.salario,
                j.origem,
                j.link,
                j.descricao,
                STRING_AGG(t.nome, ', ' ORDER BY t.nome) AS tecnologias
            FROM jobs j
            LEFT JOIN job_technologies jt ON jt.job_id = j.id
            LEFT JOIN technologies t ON t.id = jt.technology_id
            GROUP BY
                j.id, j.titulo, j.empresa, j.senioridade,
                j.localizacao, j.salario, j.origem, j.link, j.descricao
            ORDER BY j.id
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

        print(f"Exportado: {len(df)} vaga(s) -> {caminho}")
        return caminho
