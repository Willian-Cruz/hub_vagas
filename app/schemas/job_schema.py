from pydantic import BaseModel
from typing import Optional

class JobSchema(BaseModel):
    titulo:str
    empresa:str
    localizacao:str
    descricao:str
    link:Optional[str] = "Não informado"
    origem:str