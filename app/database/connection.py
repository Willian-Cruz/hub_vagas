from sqlalchemy import create_engine
from config.settings import *

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine=create_engine(DATABASE_URL)