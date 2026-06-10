from pydantic import BaseModel
from typing import Optional


class JobSchema(BaseModel):

    titulo: str
    empresa: str
    senioridade: Optional[str] = "Não informado"
    localizacao: Optional[str] = "Não informado"
    descricao: Optional[str] = "Não informado"
    salario: Optional[str] = "Não informado"  
    link: str
    origem: str