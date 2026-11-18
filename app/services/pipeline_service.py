"""
PipelineService — orquestra APENAS a ingestão de dados: coleta e raw layer `jobs`.

Responsabilidades:
    1. Coleta vagas via CollectorService (todos os scrapers)
    2. Grava vagas na tabela raw `jobs` (dedup por link / origem+id_externo)
    3. Registra status de cada fonte em bronze.scrape_runs para monitoramento
    4. Registra início, fim, duração e erros no log
    5. Trava contra execução simultânea (pg_try_advisory_lock)
    6. Notificação de falha (webhook/e-mail) quando a execução não coletar vagas

Por que separar do main.py?
    O main.py se torna apenas um ponto de entrada manual.
    O SchedulerService chama PipelineService.executar() no horário agendado.
    Testes podem chamar PipelineService.executar() de forma controlada.

Arquitetura medallion decoupled:
    - Raw (tabela jobs): scrape direto, dedup básica por link/origem+id_externo
    - Bronze (dbt): snapshot imutável a partir da raw (append-only)
    - Silver (dbt): normalização, deduplicação avançada a partir do Bronze
    - Gold (dbt): marts analíticos a partir do Silver
    - Consumo: Gold → Excel / Power BI

A transformação é responsabilidade separada, executada via `python app/transform.py`.
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from utils.logger import get_logger, log_event
from services.collector_service import CollectorService
from repositories.bronze_repository import BronzeRepository
from repositories.job_repository import DUPLICADA, ERRO, JobRepository, REVISADA, SALVA
from scrapers.base_scraper import ScrapeStatus
from database.connection import engine
from notifier import enviar_falha

logger = get_logger(__name__)

# Chave fixa do advisory lock (inteiro de 64 bits). Apenas uma execução por vez.
ADVISORY_LOCK_KEY = 1794880335682


class PipelineService:

    @staticmethod
    def _adquirir_travar_execucao():
        """Tenta adquirir o advisory lock do PostgreSQL.

        Retorna (conexao_aberta, obteve_lock). A conexao deve ser mantida aberta
        durante toda a execucao, pois locks de sessao (pg_advisory_*) pertencem
        à conexao que os adquiriu. Fechar a conexao libera o lock automaticamente.

        Se obteve_lock for False, a conexao ja foi fechada (outra instancia
        esta executando).
        """
        try:
            connection = engine.connect()
            resultado = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            ).scalar()
            connection.commit()
            if bool(resultado):
                return connection, True
            else:
                connection.close()
                return None, False
        except Exception:
            # Fail-closed: nao conseguir consultar o banco significa que nao
            # podemos garantir exclusao mutua. Abortar a execucao.
            try:
                connection.close()
            except Exception:
                pass
            log_event(
                logger=logger,
                level="ERROR",
                component="pipeline",
                stage="advisory_lock",
                event="lock_falha",
                status="falha",
                mensagem="Nao foi possível consultar o advisory lock; abortando execucao (fail-closed)",
            )
            return None, False

    @staticmethod
    def _liberar_travar_execucao(connection) -> None:
        """Libera o advisory lock na mesma conexao que o adquiriu."""
        if connection is None:
            return
        try:
            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            )
            connection.commit()
        except Exception:
            log_event(
                logger=logger,
                level="WARNING",
                component="pipeline",
                stage="advisory_lock",
                event="lock_liberacao_falha",
                status="falha",
                mensagem="Não foi possível liberar o advisory lock",
            )
        finally:
            try:
                connection.close()
            except Exception:
                pass

    @staticmethod
    def executar() -> dict:
        """
        Executa o pipeline de ingestão: coleta e persistência na raw layer `jobs`.

        Returns:
            dict com métricas da execução:
            {
                "run_id":            str,   # UUID da execução
                "coletadas":         int,   # vagas do tema retornadas pelos scrapers
                "descartadas":       int,   # vagas fora do tema, descartadas na coleta
                "raw_salvas":        int,   # vagas inseridas na tabela raw `jobs`
                "raw_duplicadas":    int,   # vagas ignoradas por já existirem
                "raw_erros":         int,   # vagas que falharam ao salvar
                "bronze_ok":         bool,  # True se os ScrapeRuns foram gravados
                "fontes":            list,  # status, contagem e erro por scraper
                "fontes_sucesso":    int,   # fontes com status SUCCESS
                "fontes_parcial":    int,   # fontes com status PARTIAL
                "fontes_falha":      int,   # fontes com status FAILED
                "fontes_vazio":      int,   # fontes com status EMPTY
                "duracao_seg":       float, # tempo total em segundos
                "sucesso":           bool,  # True se pelo menos uma fonte trouxe vagas
            }
        """
        trave_conexao, trave_adquirida = PipelineService._adquirir_travar_execucao()
        if not trave_adquirida:
            log_event(
                logger=logger,
                level="WARNING",
                component="pipeline",
                stage="advisory_lock",
                event="pipeline_bloqueado",
                status="bloqueado",
                mensagem="Outra instância do pipeline já está em execução (advisory lock). Abortando.",
            )
            return {
                "run_id": None,
                "coletadas": 0,
                "descartadas": 0,
                "raw_novas": 0,
                "raw_revisadas": 0,
                "raw_duplicadas": 0,
                "raw_erros": 0,
                "bronze_ok": False,
                "fontes": [],
                "fontes_sucesso": 0,
                "fontes_parcial": 0,
                "fontes_falha": 0,
                "fontes_vazio": 0,
                "duracao_seg": 0.0,
                "sucesso": False,
                "bloqueado_por_trava": True,
                "status": "FALHADO",
            }

        logger.info("=" * 60)
        logger.info("PIPELINE DE INGESTÃO INICIADO")
        logger.info("=" * 60)

        metricas = {
            "run_id": None,
            "coletadas":      0,
            "descartadas":    0,
            "raw_novas":      0,
            "raw_revisadas":  0,
            "raw_duplicadas": 0,
            "raw_erros":      0,
            "bronze_ok":      False,
            "fontes":         [],
            "fontes_sucesso": 0,
            "fontes_parcial": 0,
            "fontes_falha":   0,
            "fontes_vazio":   0,
            "duracao_seg":    0.0,
            "sucesso":        False,
            "bloqueado_por_trava": False,
            "status":         "FALHADO",
        }

        inicio = time.time()
        inicio_utc = datetime.now(timezone.utc)
        run_id = uuid4()
        metricas["run_id"] = str(run_id)

        log_event(
            logger=logger,
            level="INFO",
            run_id=str(run_id),
            component="pipeline",
            stage="inicio",
            event="pipeline_iniciado",
            status="iniciado",
            mensagem="PIPELINE DE INGESTÃO INICIADO",
        )

        try:
            # ── 1. Coleta ──────────────────────────────────────────────
            log_event(
                logger=logger,
                level="INFO",
                run_id=str(run_id),
                component="pipeline",
                stage="coleta",
                event="etapa_iniciada",
                status="iniciado",
                mensagem="Etapa 1/3: Coletando vagas...",
            )
            resultados = CollectorService.coletar_resultados()
            metricas["fontes"] = [
                {
                    "origem": resultado.source,
                    "status": resultado.status.value,
                    "vagas": len(resultado.jobs),
                    "paginas": resultado.pages_processed,
                    "erro": resultado.error,
                    "descartadas": resultado.discarded,
                }
                for resultado in resultados
            ]
            vagas = [vaga for resultado in resultados for vaga in resultado.jobs]
            metricas["coletadas"] = len(vagas)
            metricas["descartadas"] = sum(resultado.discarded for resultado in resultados)
            log_event(
                logger=logger,
                level="INFO",
                run_id=str(run_id),
                component="pipeline",
                stage="coleta",
                event="vagas_coletadas",
                status="sucesso",
                records_received=len(vagas),
                records_rejected=metricas["descartadas"],
                mensagem=f"Coletadas: {len(vagas)} vagas | Descartadas (fora do tema): {metricas['descartadas']}",
            )

            fontes_sucesso = []
            fontes_parcial = []
            fontes_falha = []
            fontes_vazio = []
            for resultado in resultados:
                log_event(
                    logger=logger,
                    level="INFO",
                    run_id=str(run_id),
                    component="scraper",
                    source=resultado.source,
                    stage="coleta",
                    event="fonte_resultado",
                    status=resultado.status.value,
                    records_received=len(resultado.jobs),
                    mensagem=f"Fonte {resultado.source}: {resultado.status.value} | Vagas: {len(resultado.jobs)} | Páginas: {resultado.pages_processed}",
                )
                if resultado.error:
                    log_event(
                        logger=logger,
                        level="WARNING",
                        run_id=str(run_id),
                        component="scraper",
                        source=resultado.source,
                        stage="coleta",
                        event="fonte_erro",
                        status="erro",
                        error_message=resultado.error,
                    )

                if resultado.status == ScrapeStatus.SUCCESS:
                    fontes_sucesso.append(resultado)
                elif resultado.status == ScrapeStatus.PARTIAL:
                    fontes_parcial.append(resultado)
                elif resultado.status == ScrapeStatus.FAILED:
                    fontes_falha.append(resultado)
                elif resultado.status == ScrapeStatus.EMPTY:
                    fontes_vazio.append(resultado)

            metricas["fontes_sucesso"] = len(fontes_sucesso)
            metricas["fontes_parcial"] = len(fontes_parcial)
            metricas["fontes_falha"] = len(fontes_falha)
            metricas["fontes_vazio"] = len(fontes_vazio)

            # ── 2. Raw layer: salvar na tabela `jobs` ────────────────────
            log_event(
                logger=logger,
                level="INFO",
                run_id=str(run_id),
                component="pipeline",
                stage="persistencia",
                event="etapa_iniciada",
                status="iniciado",
                mensagem="Etapa 2/3: Gravando vagas na raw layer `jobs`...",
            )
            try:
                for vaga in vagas:
                    resultado_salvamento = JobRepository.salvar(
                        vaga, run_id=run_id
                    )
                    if resultado_salvamento == SALVA:
                        metricas["raw_novas"] += 1
                    elif resultado_salvamento == REVISADA:
                        metricas["raw_revisadas"] += 1
                    elif resultado_salvamento == DUPLICADA:
                        metricas["raw_duplicadas"] += 1
                    else:
                        metricas["raw_erros"] += 1
                log_event(
                    logger=logger,
                    level="INFO",
                    run_id=str(run_id),
                    component="repository",
                    stage="persistencia",
                    event="raw_concluida",
                    status="sucesso",
                    records_received=metricas["raw_novas"],
                    records_persisted=metricas["raw_novas"],
                    records_duplicated=metricas["raw_duplicadas"],
                    records_rejected=metricas["raw_erros"],
                    mensagem=f"Raw concluída — {metricas['raw_novas']} novas, {metricas['raw_revisadas']} revistas, {metricas['raw_duplicadas']} duplicadas, {metricas['raw_erros']} erros",
                )
            except Exception:
                log_event(
                    logger=logger,
                    level="ERROR",
                    run_id=str(run_id),
                    component="repository",
                    stage="persistencia",
                    event="raw_falha",
                    status="falha",
                    mensagem="Falha ao persistir na raw layer `jobs`",
                )

            # ── 3. Bronze: registro de execução por fonte ────────────────
            log_event(
                logger=logger,
                level="INFO",
                run_id=str(run_id),
                component="pipeline",
                stage="bronze",
                event="etapa_iniciada",
                status="iniciado",
                mensagem="Etapa 3/3: Gravando status de execução no Bronze...",
            )
            bronze_ok = False
            try:
                metricas_bronze = BronzeRepository.persistir_resultados(
                    resultados,
                    run_id=run_id,
                    started_at=inicio_utc,
                    finished_at=datetime.now(timezone.utc),
                )
                bronze_ok = True
                metricas["bronze_ok"] = True
                log_event(
                    logger=logger,
                    level="INFO",
                    run_id=str(run_id),
                    component="repository",
                    stage="bronze",
                    event="bronze_concluida",
                    status="sucesso",
                    records_persisted=metricas_bronze,
                    mensagem=f"Bronze concluída — {metricas_bronze} scrape_run(s) registrado(s)",
                )
            except Exception:
                log_event(
                    logger=logger,
                    level="ERROR",
                    run_id=str(run_id),
                    component="repository",
                    stage="bronze",
                    event="bronze_falha",
                    status="falha",
                    mensagem="Falha ao persistir status no Bronze",
                )

            # Sucesso parcial ou total = Bronze gravado e pelo menos uma fonte
            # retornou dados (SUCESSO ou PARTIAL com vagas).
            # Erros de persistência na raw impedem status SUCESSO integral.
            fontes_com_vagas = fontes_sucesso + [f for f in fontes_parcial if f.jobs]
            tem_dados = len(fontes_com_vagas) > 0
            todas_sucesso = len(fontes_sucesso) == len(resultados) and len(resultados) > 0
            tem_erros_persistencia = metricas["raw_erros"] > 0
            persistiu_alguma = metricas["raw_novas"] > 0 or metricas["raw_revisadas"] > 0

            if tem_erros_persistencia and not persistiu_alguma:
                # Erro de persistência em todas as vagas: falha total
                metricas["sucesso"] = False
                metricas["status"] = "FALHADO"
            elif tem_erros_persistencia and persistiu_alguma:
                # Algumas vagas persistidas, outras falharam: parcial
                metricas["sucesso"] = False
                metricas["status"] = "PARTIAL"
            elif bronze_ok and tem_dados:
                metricas["sucesso"] = True
                metricas["status"] = "SUCESSO" if todas_sucesso else "PARTIAL"
            elif bronze_ok and not tem_dados:
                # Bronze funcionou, mas nenhuma fonte trouxe dados
                metricas["sucesso"] = False
                metricas["status"] = "FALHADO"
            else:
                # Bronze nao funcionou (erro de persistência)
                metricas["sucesso"] = False
                metricas["status"] = "FALHADO"

            if metricas["fontes_falha"] > 0:
                log_event(
                    logger=logger,
                    level="WARNING",
                    run_id=str(run_id),
                    component="pipeline",
                    stage="finalizacao",
                    event="fontes_falha",
                    status="aviso",
                    records_rejected=metricas["fontes_falha"],
                    mensagem=f"Pipeline concluído com {metricas['fontes_falha']} fonte(s) em falha",
                )
            if metricas["fontes_parcial"] > 0:
                log_event(
                    logger=logger,
                    level="INFO",
                    run_id=str(run_id),
                    component="pipeline",
                    stage="finalizacao",
                    event="fontes_parcial",
                    status="aviso",
                    mensagem=f"Pipeline concluído com {metricas['fontes_parcial']} fonte(s) parcial(is)",
                )
            if not metricas["sucesso"]:
                if metricas["status"] == "FALHADO":
                    log_event(
                        logger=logger,
                        level="WARNING",
                        run_id=str(run_id),
                        component="pipeline",
                        stage="finalizacao",
                        event="pipeline_sem_sucesso",
                        status="falha",
                        mensagem="Pipeline não coletou vagas de nenhuma fonte",
                    )
                    enviar_falha(metricas, erro="nenhuma fonte trouxe vagas")
                else:
                    # PARTIAL: loga aviso, mas não envia notificação de falha
                    log_event(
                        logger=logger,
                        level="WARNING",
                        run_id=str(run_id),
                        component="pipeline",
                        stage="finalizacao",
                        event="pipeline_parcial",
                        status="parcial",
                        mensagem="Pipeline concluído parcialmente — algumas fontes falharam ou não trouxeram vagas",
                    )

        except Exception as e:
            log_event(
                logger=logger,
                level="ERROR",
                run_id=str(run_id),
                component="pipeline",
                stage="finalizacao",
                event="erro_critico",
                status="falha",
                error_type=type(e).__name__,
                error_message=str(e),
                mensagem=f"Erro crítico no pipeline: {e}",
            )
            metricas["sucesso"] = False
            enviar_falha(metricas, erro=str(e))

        finally:
            PipelineService._liberar_travar_execucao(trave_conexao)
            metricas["duracao_seg"] = round(time.time() - inicio, 2)
            status_final = metricas["status"]
            log_event(
                logger=logger,
                level="INFO",
                run_id=str(run_id),
                component="pipeline",
                stage="finalizacao",
                event="pipeline_finalizado",
                status=status_final.lower(),
                duration_ms=round(metricas["duracao_seg"] * 1000, 2),
                records_received=metricas["coletadas"],
                records_persisted=metricas["raw_novas"],
                records_duplicated=metricas["raw_duplicadas"],
                records_rejected=metricas["raw_erros"],
                mensagem=(
                    f"PIPELINE {status_final} em {metricas['duracao_seg']}s | "
                    f"Coletadas: {metricas['coletadas']} | "
                    f"Descartadas: {metricas['descartadas']} | "
                    f"Raw: {metricas['raw_novas']} novas / "
                    f"{metricas['raw_revisadas']} revistas / "
                    f"{metricas['raw_duplicadas']} dup / {metricas['raw_erros']} err | "
                    f"Fontes: {metricas['fontes_sucesso']} ok, {metricas['fontes_parcial']} parcial, {metricas['fontes_falha']} falha, {metricas['fontes_vazio']} vazio"
                ),
            )

        return metricas