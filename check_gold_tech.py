import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(
    f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@'
    f'{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)

with engine.connect() as conn:
    result = conn.execute(text("""
        select
            count(*) as total,
            sum(case when tecnologias <> '' and tecnologias is not null then 1 else 0 end) as com_tecnologias,
            round(100.0 * sum(case when tecnologias <> '' and tecnologias is not null then 1 else 0 end) / nullif(count(*), 0), 1) as pct
        from gold.mart_vagas
    """))
    for row in result:
        print(f"Total: {row[0]}, Com tecnologias: {row[1]}, %: {row[2]}%")
    
    # Check by origem
    result = conn.execute(text("""
        select
            origem,
            count(*) as total,
            sum(case when tecnologias <> '' and tecnologias is not null then 1 else 0 end) as com_tecnologias,
            round(100.0 * sum(case when tecnologias <> '' and tecnologias is not null then 1 else 0 end) / nullif(count(*), 0), 1) as pct
        from gold.mart_vagas
        group by origem
    """))
    print("\nPor origem:")
    for row in result:
        print(f"  {row[0]}: {row[1]} total, {row[2]} com tech ({row[3]}%)")