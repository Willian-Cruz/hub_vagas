import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(
    f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@'
    f'{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)

with engine.connect() as conn:
    # Check raw jobs by origem
    result = conn.execute(text("""
        SELECT origem, count(*) as total, 
               min(data_coleta) as primeira, max(data_coleta) as ultima
        FROM public.jobs
        GROUP BY origem
        ORDER BY origem
    """))
    print("public.jobs por origem:")
    for row in result:
        print(f"  {row[0]}: {row[1]} vagas ({row[2]} a {row[3]})")
    
    # Check bronze scrape_runs
    print("\nbronze.scrape_runs:")
    result = conn.execute(text("""
        SELECT source, count(*) as runs, 
               sum(jobs_found) as total_jobs_found,
               min(finished_at) as primeira, max(finished_at) as ultima
        FROM bronze.scrape_runs
        GROUP BY source
        ORDER BY source
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]} runs, {row[2]} jobs_found ({row[3]} a {row[4]})")
    
    # Check distinct Catho links
    print("\nVagas Catho na raw (distinct link):")
    result = conn.execute(text("""
        SELECT count(DISTINCT link) FROM public.jobs WHERE origem = 'Catho'
    """))
    for row in result:
        print(f"  {row[0]}")
        
    # Check if Catho jobs are being filtered by relevance
    # Let's look at some Catho job titles
    print("\nTítulos de vagas Catho (sample):")
    result = conn.execute(text("""
        SELECT titulo FROM public.jobs WHERE origem = 'Catho' LIMIT 20
    """))
    for row in result:
        print(f"  {row[0]}")