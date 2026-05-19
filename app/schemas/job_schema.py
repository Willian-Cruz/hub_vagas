from pydantic import BaseModel

class JobSchema(BaseModel):
    titulo:str
    empresa:str
    localizacao:str
    descricao:str
    link:str
    origem:str