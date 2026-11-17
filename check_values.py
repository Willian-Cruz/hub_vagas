import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(
    f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@'
    f'{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)

with engine.connect() as conn:
    result = conn.execute(text('SELECT DISTINCT origem FROM public.jobs'))
    print('public.jobs.origem values:')
    for row in result:
        print(f'  {repr(row[0])}')
    print()
    result = conn.execute(text('SELECT DISTINCT source FROM bronze.scrape_runs'))
    print('bronze.scrape_runs.source values:')
    for row in result:
        print(f'  {repr(row[0])}')