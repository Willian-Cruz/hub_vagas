# Registra a tarefa "HubVagas\ColetaDiaria" no Agendador de Tarefas do Windows.
#
# Executa app/main.py (ingestão) seguido de app/transform.py (dbt build)
# todo dia às 06:00, horário de São Paulo. Se o PC estiver dormindo às 06:00,
# a tarefa é disparada assim que possível após a inicialização.
#
# Uso (PowerShell, como Administrador):
#   .\scripts\registrar_tarefa_coletadiaria.ps1

$ErrorActionPreference = "Stop"

$tarefaNome   = "HubVagas\ColetaDiaria"
$xmlCaminho   = "$PSScriptRoot\..\scripts\task_hub_vagas_coletadiaria.xml"
$descricao    = "Hub Vagas — coleta diária de vagas (06:00 São Paulo) + dbt build"

# Remove tarefa existente, se houver
if (Get-ScheduledTask -TaskName $tarefaNome.Split('\')[1] -TaskPath $tarefaNome.Split('\')[0] -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $tarefaNome.Split('\')[1] -TaskPath $tarefaNome.Split('\')[0] -Confirm:$false
    Write-Host "Tarefa existente removida."
}

# Registra a nova tarefa
Register-ScheduledTask -Xml (Get-Content $xmlCaminho -Raw) -TaskName $tarefaNome -User $env:USERNAME
Write-Host "Tarefa '$tarefaNome' registrada com sucesso."
Write-Host "Para executar manualmente agora: Start-ScheduledTask -TaskName '$tarefaNome.Split('\')[1]' -TaskPath '$tarefaNome.Split('\')[0]'"
