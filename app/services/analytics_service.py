import pandas as pd
from sqlalchemy import text
from database.connection import engine


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
            FROM jobs
            WHERE senioridade != 'Não informado'
              AND senioridade IS NOT NULL
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
            FROM jobs
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
        'Presencial' é inferido: tudo que tem cidade/estado definida.
        """
        sql = """
            SELECT
                CASE
                    WHEN localizacao = 'Remoto'  THEN 'Remoto'
                    WHEN localizacao = 'Híbrido' THEN 'Híbrido'
                    WHEN localizacao = 'Não informado' THEN 'Não informado'
                    ELSE 'Presencial'
                END AS label,
                COUNT(*) AS total
            FROM jobs
            GROUP BY label
            ORDER BY total DESC
        """
        return cls._query(sql)

    @classmethod
    def top_tecnologias(cls, top_n: int = 15) -> pd.DataFrame:
        """
        Top N tecnologias mais mencionadas nas vagas.
        Faz o join com a tabela de relacionamento many-to-many.
        """
        sql = f"""
            SELECT
                t.nome  AS label,
                COUNT(*) AS total
            FROM technologies t
            JOIN job_technologies jt ON jt.technology_id = t.id
            GROUP BY t.nome
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
            FROM jobs
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
            FROM jobs
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
            FROM jobs
        """
        df = cls._query(sql)
        row = df.iloc[0]

        # Total de tecnologias vem de outra tabela
        df_tech = cls._query("SELECT COUNT(*) AS total FROM technologies")
        total_tech = int(df_tech.iloc[0]["total"])

        return {
            "total_vagas": int(row["total_vagas"]),
            "total_empresas": int(row["total_empresas"]),
            "total_portais": int(row["total_portais"]),
            "total_techs": total_tech,
        }
