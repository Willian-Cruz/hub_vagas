import pandas as pd
from sqlalchemy import text

from app.database.connection import engine


class AnalyticsService:

    # ─────────────────────────────────────────────────────────────
    # HELPERS INTERNOS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _query(sql: str) -> pd.DataFrame:
        """Executa uma query e retorna um DataFrame."""
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)

    # ─────────────────────────────────────────────────────────────
    # INDICADORES
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def vagas_por_senioridade(cls) -> pd.DataFrame:
        """
        Conta quantas vagas existem por nível de senioridade.
        Exclui 'Não informado' para não poluir o gráfico.
        """
        sql = """
            SELECT
                senioridade AS label,
                COUNT(*)    AS total
            FROM gold.mart_vagas
            WHERE senioridade IS NOT NULL
              AND senioridade != 'Não informado'
            GROUP BY senioridade
            ORDER BY total DESC
        """
        return cls._query(sql)

    @classmethod
    def vagas_por_localizacao(cls, top_n: int = 10) -> pd.DataFrame:
        """
        Top N cidades/estados com mais vagas.
        Exclui 'Não informado', 'Remoto' e 'Híbrido' para
        focar na distribuição geográfica real.
        """
        sql = f"""
            SELECT
                localizacao AS label,
                COUNT(*)    AS total
            FROM gold.mart_vagas
            WHERE localizacao NOT IN ('Não informado', 'Remoto', 'Híbrido')
              AND localizacao IS NOT NULL
            GROUP BY localizacao
            ORDER BY total DESC
            LIMIT {top_n}
        """
        return cls._query(sql)

    @classmethod
    def vagas_por_modalidade(cls) -> pd.DataFrame:
        """
        Distribuição entre Remoto, Híbrido e Presencial.
        Usa a modalidade informada pelo portal quando existe; senão,
        'Presencial' é inferido: tudo que tem cidade/estado definida.
        Local NULL (sem informação) fica como 'Não informado'.
        """
        sql = """
            SELECT
                CASE
                    WHEN modalidade IS NOT NULL   THEN modalidade
                    WHEN localizacao = 'Remoto'   THEN 'Remoto'
                    WHEN localizacao = 'Híbrido'  THEN 'Híbrido'
                    WHEN localizacao IS NULL
                      OR localizacao = 'Não informado' THEN 'Não informado'
                    ELSE 'Presencial'
                END AS label,
                COUNT(*) AS total
            FROM gold.mart_vagas
            GROUP BY label
            ORDER BY total DESC
        """
        return cls._query(sql)

    @classmethod
    def top_tecnologias(cls, top_n: int = 15) -> pd.DataFrame:
        """
        Top N tecnologias mais mencionadas nas vagas.
        Utiliza a coluna tecnologias do mart Gold, que contém os termos
        separados por vírgula extraídos das descrições.
        """
        sql = f"""
            SELECT
                unnest(string_to_array(tecnologias, ',')) AS label,
                COUNT(*) AS total
            FROM gold.mart_vagas
            WHERE tecnologias IS NOT NULL AND tecnologias != ''
            GROUP BY label
            ORDER BY total DESC
            LIMIT {top_n}
        """
        return cls._query(sql)

    @classmethod
    def vagas_por_origem(cls) -> pd.DataFrame:
        """Quantas vagas vieram de cada portal."""
        sql = """
            SELECT
                origem   AS label,
                COUNT(*) AS total
            FROM gold.mart_vagas
            GROUP BY origem
            ORDER BY total DESC
        """
        return cls._query(sql)

    @classmethod
    def distribuicao_salarios(cls) -> pd.DataFrame:
        """
        Conta vagas por status de salário:
        informado (tem R$), a combinar, não informado.
        """
        sql = """
            SELECT
                CASE
                    WHEN salario LIKE '%R$%'       THEN 'Salário informado'
                    WHEN salario = 'A combinar'    THEN 'A combinar'
                    ELSE                                'Não informado'
                END AS label,
                COUNT(*) AS total
            FROM gold.mart_vagas
            GROUP BY label
            ORDER BY total DESC
        """
        return cls._query(sql)

    @classmethod
    def resumo_geral(cls) -> dict:
        """
        Retorna um dicionário com os números do cabeçalho do dashboard:
        total de vagas, empresas únicas, tecnologias mapeadas e portais.
        """
        sql = """
            SELECT
                COUNT(*)                        AS total_vagas,
                COUNT(DISTINCT empresa)         AS total_empresas,
                COUNT(DISTINCT origem)          AS total_portais
            FROM gold.mart_vagas
        """
        df = cls._query(sql)
        row = df.iloc[0]

        # Total de tecnologias vem do mart_demanda_tecnologias (Gold),
        # extraído por regex da seed tecnologias_monitoradas.csv.
        df_tech = cls._query(
            "SELECT COUNT(*) AS total FROM gold.mart_demanda_tecnologias"
        )
        total_tech = int(df_tech.iloc[0]["total"])

        return {
            "total_vagas": int(row["total_vagas"]),
            "total_empresas": int(row["total_empresas"]),
            "total_portais": int(row["total_portais"]),
            "total_techs": total_tech,
        }
