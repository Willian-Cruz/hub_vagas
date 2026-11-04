from datetime import datetime

from sqlalchemy.exc import IntegrityError

from database.connection import SessionLocal
from database.job_model import Job
from database.tech_model import Technology
from services.tech_service import TechnologyService
from services.normalize_service import NormalizeService
from services.salary_service import SalaryService
from utils.logger import get_logger
from utils.text_utils import chave_conteudo, valor_ou_none

logger = get_logger(__name__)

# Resultados possíveis de JobRepository.salvar().
# O PipelineService usa esses valores para montar as métricas da execução.
SALVA = "salva"
DUPLICADA = "duplicada"
ERRO = "erro"

# Restrições UNIQUE que significam "essa vaga já existe".
_CONSTRAINTS_UNICAS = {"jobs_link_key", "uq_jobs_link", "uq_jobs_origem_id_externo"}

# Campos que uma vaga já gravada recebe quando estavam NULL e a coleta traz valor.
# Nunca sobrescreve um valor que já existe.
_CAMPOS_PREENCHIVEIS = (
    "empresa",
    "senioridade",
    "localizacao",
    "descricao",
    "salario",
    "id_externo",
    "data_publicacao",
    "modalidade",
    "experiencia",
    "escolaridade",
    "qtd_posicoes",
    "chave_conteudo",
)


def _violacao_de_link_unico(erro: IntegrityError) -> bool:
    """Identifica a UNIQUE da vaga (link ou origem+id_externo) sem mascarar outras violações."""
    origem = getattr(erro, "orig", None)
    diagnostico = getattr(origem, "diag", None)
    constraint = getattr(diagnostico, "constraint_name", None)
    mensagem = f"{erro} {origem}".lower()

    return (
        constraint in _CONSTRAINTS_UNICAS
        or "jobs.link" in mensagem
        or "jobs_link_key" in mensagem
        or "uq_jobs_origem_id_externo" in mensagem
        or "jobs.origem, jobs.id_externo" in mensagem
        or "link duplicado" in mensagem
    )


class JobRepository:

    @staticmethod
    def _normalizar(vaga) -> dict:
        """Campos da vaga já normalizados; None onde não há informação."""
        senioridade = NormalizeService.normalizar_senioridade(
            vaga.senioridade
        ) or NormalizeService.normalizar_senioridade(vaga.titulo, de_titulo=True)
        localizacao = NormalizeService.normalizar_localizacao(vaga.localizacao)
        empresa = NormalizeService.normalizar_empresa(vaga.empresa)
        descricao = valor_ou_none(vaga.descricao)

        # Salário: primeiro o campo do card (InfoJobs); senão, procura na descrição.
        salario = SalaryService.extrair(vaga.salario) or SalaryService.extrair(descricao)

        # Modalidade: a do card; senão a que o próprio local informa ("Home Office").
        modalidade = NormalizeService.normalizar_modalidade(vaga.modalidade)
        if modalidade is None and localizacao in ("Remoto", "Híbrido"):
            modalidade = localizacao

        return {
            "empresa": empresa,
            "senioridade": senioridade,
            "localizacao": localizacao,
            "descricao": descricao,
            "salario": salario,
            "id_externo": valor_ou_none(vaga.id_externo),
            "data_publicacao": vaga.data_publicacao,
            "modalidade": modalidade,
            "experiencia": valor_ou_none(vaga.experiencia),
            "escolaridade": valor_ou_none(vaga.escolaridade),
            "qtd_posicoes": vaga.qtd_posicoes,
            "chave_conteudo": chave_conteudo(
                vaga.origem, vaga.titulo, empresa, localizacao
            ),
        }

    @staticmethod
    def _buscar_existente(session, vaga, dados):
        """Procura a vaga no banco. Devolve (Job ou None, critério que casou)."""
        existente = session.query(Job).filter(Job.link == vaga.link).first()
        if existente:
            return existente, "link"

        if dados["id_externo"]:
            existente = (
                session.query(Job)
                .filter(Job.origem == vaga.origem, Job.id_externo == dados["id_externo"])
                .first()
            )
            if existente:
                return existente, "id_externo"

        if dados["chave_conteudo"]:
            existente = (
                session.query(Job)
                .filter(Job.chave_conteudo == dados["chave_conteudo"])
                .first()
            )
            if existente:
                return existente, "conteudo"

        return None, None

    @staticmethod
    def _preencher_vazios(existente, dados, ignorar=()) -> list:
        """Preenche campos NULL da vaga já gravada. Devolve os nomes preenchidos."""
        preenchidos = []
        for campo in _CAMPOS_PREENCHIVEIS:
            if campo in ignorar:
                continue
            novo = dados.get(campo)
            if novo is not None and getattr(existente, campo, None) is None:
                setattr(existente, campo, novo)
                preenchidos.append(campo)
        return preenchidos

    @staticmethod
    def salvar(vaga) -> str:
        """
        Persiste uma vaga normalizada, com as tecnologias extraídas da descrição.

        Se a vaga já existe (mesmo link, mesmo ID no portal ou mesmo conteúdo),
        não cria outra linha, mas preenche os campos que estavam NULL.

        Returns:
            "salva"      — a vaga foi inserida
            "duplicada"  — já existia uma vaga igual
            "erro"       — falha ao salvar (a transação sofre rollback)
        """

        session = SessionLocal()

        try:
            dados = JobRepository._normalizar(vaga)

            # ── Verifica duplicata: link, ID no portal ou conteúdo ────
            existente, criterio = JobRepository._buscar_existente(session, vaga, dados)

            if existente:
                # Em duplicata por conteúdo o ID é de OUTRO anúncio: não herda.
                ignorar = ("id_externo",) if criterio == "conteudo" else ()
                preenchidos = JobRepository._preencher_vazios(existente, dados, ignorar)
                if preenchidos:
                    session.commit()
                    logger.info(
                        "Vaga já existia (%s); campos preenchidos: %s | %s",
                        criterio, ", ".join(preenchidos), vaga.titulo,
                    )
                elif criterio == "conteudo":
                    logger.info(
                        "Vaga repetida por conteúdo (outro ID no portal): %s", vaga.link
                    )
                else:
                    logger.info("Vaga já existe: %s", vaga.titulo)
                return DUPLICADA

            # ── Cria o objeto Job com dados normalizados ──────────────
            nova_vaga = Job(
                titulo=vaga.titulo,
                link=vaga.link,
                origem=vaga.origem,
                data_coleta=datetime.now(),
                **dados,
            )

            session.add(nova_vaga)

            # ── Extrai e vincula tecnologias ──────────────────────────
            tecnologias = TechnologyService.extrair(dados["descricao"])

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

            session.commit()

            logger.info(
                f"Salva: {vaga.titulo} | "
                f"Senioridade: {dados['senioridade']} | "
                f"Local: {dados['localizacao']} | "
                f"Salário: {dados['salario']}"
            )
            return SALVA

        except IntegrityError as erro:
            session.rollback()
            if _violacao_de_link_unico(erro):
                logger.info("Vaga duplicada detectada durante o commit: %s", vaga.link)
                return DUPLICADA

            logger.exception("Violação de integridade ao salvar vaga %s", vaga.link)
            return ERRO

        except Exception:
            session.rollback()
            logger.exception("Erro inesperado ao salvar vaga %s", vaga.link)
            return ERRO

        finally:
            session.close()
