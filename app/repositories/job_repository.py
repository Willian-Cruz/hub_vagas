from datetime import datetime

from sqlalchemy.exc import IntegrityError

from database.connection import SessionLocal
from database.job_model import Job
from database.tech_model import Technology
from services.tech_service import TechnologyService
from services.normalize_service import NormalizeService
from services.salary_service import SalaryService
from utils.logger import get_logger

logger = get_logger(__name__)

# Resultados possíveis de JobRepository.salvar().
# O PipelineService usa esses valores para montar as métricas da execução.
SALVA = "salva"
DUPLICADA = "duplicada"
ERRO = "erro"


class JobRepository:

    @staticmethod
    def salvar(vaga) -> str:
        """
        Persiste uma vaga normalizada, com as tecnologias extraídas da descrição.

        Returns:
            "salva"      — a vaga foi inserida
            "duplicada"  — já existia uma vaga com o mesmo link
            "erro"       — falha ao salvar (a transação sofre rollback)
        """

        session = SessionLocal()

        try:
            # ── Verifica duplicata pelo link ──────────────────────────
            vaga_existente = session.query(Job).filter(Job.link == vaga.link).first()

            if vaga_existente:
                logger.info(f"Vaga já existe: {vaga.titulo}")
                return DUPLICADA

            # ── Sprint 5: normalização antes de salvar ────────────────

            senioridade_norm = NormalizeService.normalizar_senioridade(vaga.senioridade)
            localizacao_norm = NormalizeService.normalizar_localizacao(vaga.localizacao)
            empresa_norm = NormalizeService.normalizar_empresa(vaga.empresa)

            # Extrai salário da descrição (campo dedicado ainda não existe nos scrapers)
            salario = SalaryService.extrair(vaga.descricao)

            # ── Cria o objeto Job com dados normalizados ──────────────
            nova_vaga = Job(
                titulo=vaga.titulo,
                empresa=empresa_norm,
                senioridade=senioridade_norm,
                localizacao=localizacao_norm,
                descricao=vaga.descricao,
                salario=salario,
                link=vaga.link,
                origem=vaga.origem,
                data_coleta=datetime.now(),
            )

            session.add(nova_vaga)

            # ── Extrai e vincula tecnologias ──────────────────────────
            tecnologias = TechnologyService.extrair(vaga.descricao)

            for tech_nome in tecnologias:

                tecnologia = (
                    session.query(Technology)
                    .filter(Technology.nome == tech_nome)
                    .first()
                )

                if not tecnologia:
                    tecnologia = Technology(nome=tech_nome)
                    session.add(tecnologia)
                    session.flush()

                nova_vaga.technologies.append(tecnologia)

            session.add(nova_vaga)
            session.commit()

            logger.info(
                f"Salva: {vaga.titulo} | "
                f"Senioridade: {senioridade_norm} | "
                f"Local: {localizacao_norm} | "
                f"Salário: {salario}"
            )
            return SALVA

        except IntegrityError:
            # A restrição UNIQUE do link é a garantia final contra duplicatas,
            # inclusive quando dois processos salvam a mesma vaga ao mesmo tempo.
            session.rollback()
            logger.info(f"Vaga duplicada (restrição UNIQUE no link): {vaga.titulo}")
            return DUPLICADA

        except Exception as e:
            session.rollback()
            logger.error(f"Erro ao salvar vaga '{vaga.titulo}': {e}")
            return ERRO

        finally:
            session.close()
