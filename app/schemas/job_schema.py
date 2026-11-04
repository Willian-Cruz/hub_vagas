from pydantic import BaseModel
from pydantic import Field
from typing import Any, Optional


class JobSchema(BaseModel):

    titulo: str
    empresa: str
    senioridade: Optional[str] = "Não informado"
    localizacao: Optional[str] = "Não informado"
    descricao: Optional[str] = "Não informado"
    salario: Optional[str] = "Não informado"  
    link: str
    origem: str
    # O fragmento é mantido para Bronze, mas não integra o contrato normalizado.
    raw_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)
