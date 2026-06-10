from database.connection import Sessionlocal
from database.job_model import Job
from database.tech_model import Technology
from services.tech_service import TechnologyService
from services.normalize_service import NormalizeService
from services.salary_service import SalaryService


class JobRepository:

    @staticmethod
    def salvar(vaga):

        session = Sessionlocal()

        try:
            # ── Verifica duplicata pelo link ──────────────────────────
            vaga_existente = session.query(Job).filter(Job.link == vaga.link).first()

            if vaga_existente:
                print(f"Vaga já existe: {vaga.titulo}")
                return

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

            print(
                f"Salva: {vaga.titulo} | "
                f"Senior: {senioridade_norm} | "
                f"Local: {localizacao_norm} | "
                f"Salário: {salario}"
            )

        except Exception as e:
            session.rollback()
            print(f"Erro ao salvar vaga: {e}")

        finally:
            session.close()
