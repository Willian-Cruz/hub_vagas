<#
.SYNOPSIS
    Tarefa diária do Hub Vagas: executa a ingestão (main.py) e, se bem-sucedida,
    a transformação (dbt build via transform.py).

.DESCRIPTION
    Este script é destinado ao Agendador de Tarefas do Windows.
    Configuração recomendada:
      - Gatilho: diário, 06:00 (horário de São Paulo)
      - "Executar a tarefa assim que possível após uma execução perdida": HABILITADO
      - Se a tarefa já estiver em execução, não iniciar uma nova instância
      - Ação: powershell.exe -ExecutionPolicy Bypass -File "caminho\hub_vagas_diario.ps1"

.NOTES
    Requer: Python instalado, venv ativado (ou caminhos absolutos), .env configurado,
    PostgreSQL acessível e dbt instalado para a transformação.
#>
$ErrorActionPreference = "Stop"

# ── Caminhos (ajuste se necessário) ──────────────────────────────────────────
$repoRoot = "C:\Users\Cliente\Desktop\Portfolio\hub_vagas"
$python   = "$repoRoot\.venv\Scripts\python.exe"
$mainPy   = "$repoRoot\app\main.py"
$transformPy = "$repoRoot\app\transform.py"
$logFile  = "$repoRoot\infra\task_scheduler\hub_vagas_diario.log"

function Escrever-Log($mensagem) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $linha = "[$timestamp] $mensagem"
    Write-Host $linha
    Add-Content -Path $logFile -Value $linha -Encoding UTF8
}

try {
    Escrever-Log "=== Início da tarefa diária Hub Vagas ==="
    Escrever-Log "Diretório: $repoRoot"

    # Verifica se o Python existe
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python não encontrado em: $python"
    }

    # ── Etapa 1: Ingestão (main.py) ──────────────────────────────────────
    Escrever-Log "Etapa 1/2: Executando ingestão (main.py)..."
    $procIngestao = & $python $mainPy
    $codigoSaidaIngestao = $LASTEXITCODE

    if ($codigoSaidaIngestao -ne 0) {
        Escrever-Log "ERRO: Ingestão falhou com código de saída $codigoSaidaIngestao"
        # Notificação de falha (se houver webhook configurado no .env)
        throw "Ingestão falhou com código $codigoSaidaIngestao"
    }

    Escrever-Log "Ingestão concluída com sucesso."

    # ── Etapa 2: Transformação (dbt build via transform.py) ──────────────
    Escrever-Log "Etapa 2/2: Executando transformação (transform.py)..."
    $procTransformacao = & $python $transformPy
    $codigoSaidaTransformacao = $LASTEXITCODE

    if ($codigoSaidaTransformacao -ne 0) {
        Escrever-Log "ERRO: Transformação falhou com código de saída $codigoSaidaTransformacao"
        throw "Transformação falhou com código $codigoSaidaTransformacao"
    }

    Escrever-Log "Transformação concluída com sucesso."
    Escrever-Log "=== Tarefa diária Hub Vagas concluída com sucesso ==="
    exit 0
}
catch {
    Escrever-Log "ERRO CRÍTICO: $_"
    exit 1
}
