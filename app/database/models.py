from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

base = declarative_base()

class Job(base):
    __tablename__ = "job"
    id=Column(Integer, primary_key=True)
    titulo=Column(String)
    empresa=Column(String)
    localizacao=Column(String)
    descricao=Column(Text)
    link=Column(Text, unique=True, nullable=False)
    origem=Column(String)