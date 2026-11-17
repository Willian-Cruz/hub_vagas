import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(
    f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@'
    f'{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)

with engine.connect() as conn:
    # Check freshness
    result = conn.execute(text("""
        select max(data_coleta) as ultima_coleta,
               now() as agora,
               extract(epoch from (now() - max(data_coleta))) / 3600 as horas_desde_coleta
        from silver.jobs
    """))
    for row in result:
        print(f"Freshness: ultima_coleta={row[0]}, horas_desde_coleta={row[2]:.1f}h")
    
    # Check null percentages
    result = conn.execute(text("""
        select
            count(*) as total,
            sum(case when empresa is null then 1 else 0 end) as empresa_null,
            sum(case when localizacao is null then 1 else 0 end) as localizacao_null,
            sum(case when senioridade is null then 1 else 0 end) as senioridade_null,
            sum(case when modalidade is null then 1 else 0 end) as modalidade_null,
            sum(case when salario is null then 1 else 0 end) as salario_null,
            sum(case when descricao is null then 1 else 0 end) as descricao_null
        from silver.jobs
    """))
    for row in result:
        total = row[0]
        print(f"\nTotal registros: {total}")
        for i, campo in enumerate(['empresa', 'localizacao', 'senioridade', 'modalidade', 'salario', 'descricao']):
            nulls = row[i+1]
            pct = 100.0 * nulls / total if total > 0 else 0
            status = "FAIL" if (campo != 'salario' and pct > 50) or (campo == 'salario' and pct > 90) else "OK"
            print(f"  {campo}: {nulls}/{total} = {pct:.1f}% NULL {status}")