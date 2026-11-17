import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(
    f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@'
    f'{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)

with engine.connect() as conn:
    # Check Silver jobs by origem
    result = conn.execute(text("""
        SELECT origem, count(*) as total
        FROM silver.jobs
        GROUP BY origem
        ORDER BY origem
    """))
    print("silver.jobs por origem:")
    for row in result:
        print(f"  {row[0]}: {row[1]} vagas")
    
    # Check if Catho has any in Silver
    result = conn.execute(text("""
        SELECT count(*) FROM silver.jobs WHERE origem = 'Catho'
    """))
    for row in result:
        print(f"\nCatho no Silver: {row[0]}")
    
    # Check raw Catho titles vs relevance filter
    print("\nTeste relevância Catho (sample):")
    from utils.text_utils import sem_acentos
    import re
    TERMOS = ("dados","data","database","analytics","business intelligence","bi","etl","dbt","machine learning","inteligencia artificial","ia","dba","sql","python","spark","airflow","databricks","snowflake","bigquery")
    padrao = r"\b(?:" + "|".join(re.escape(t) for t in TERMOS) + r")\b"
    
    result = conn.execute(text("""
        SELECT titulo FROM public.jobs WHERE origem = 'Catho' LIMIT 30
    """))
    for row in result:
        titulo = row[0]
        texto = sem_acentos(str(titulo)).casefold()
        match = re.search(padrao, texto) is not None
        print(f"  {'✓' if match else '✗'} {titulo}")