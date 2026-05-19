from database.connection import engine
from database.models import base
from config.settings import *


base.metadata.create_all(engine)
print("Banco criado com sucesso!")