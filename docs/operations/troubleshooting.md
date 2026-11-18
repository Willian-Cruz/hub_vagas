# Operações e Troubleshooting — Hub Vagas

Procedimentos operacionais e resolução de problemas comuns.

---

## Execução diária

O pipeline roda via Agendador de Tarefas do Windows (tarefa `HubVagas\ColetaDiaria`) todo dia às 06:00, horário de São Paulo.

### Registrar a tarefa (Primeira vez)

```powershell
# PowerShell como Administrador
.\scripts\registrar_tarefa_coletadiaria.ps1
```

### Executar manualmente

```bash
# Ingestão (coleta → raw)
python app/main.py

# Transformação (raw → Silver → Gold)
python app/transform.py

# Ambas em sequência
python app/scheduler.py --com-transformacao
```

---

## Troubleshooting

### Problema: Nenhuma vaga é coletada

**Possíveis causas:**

1. **Portal mudou o layout HTML:** Os seletores CSS dos scrapers podem ter quebrado.
   - Verifique os logs em `logs/pipeline.log`.
   - Atualize os seletores em `app/scrapers/<portal>_scraper.py`.
   - Adicione fixtures de HTML real em `app/tests/fixtures/` e atualize os testes.

2. **Problema de rede/TLS:** O InfoJobs pode falhar na validação de certificado em redes corporativas.
   - Configure `REQUESTS_CA_BUNDLE` com o certificado CA da rede.
   - Ou defina `DB_SSLMODE=disable` (apenas para bancos que não exigem TLS).

3. **Filtro de relevância muito restritivo:** Verifique `dbt/seeds/termos_relevancia.csv`.

### Problema: dbt build falha

**Possíveis causas:**

1. **Banco não está rodando:** Verifique se o PostgreSQL está ativo.
2. **Credenciais incorretas:** Verifique o `.env` (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME).
3. **Migrações pendentes:** Execute `python infra/migrate.py` para aplicar migrações pendentes.
4. **Colunas ausentes na raw:** Se adicionou campos ao `JobSchema`, verifique se a migration correspondente foi aplicada.

### Problema: Pipeline travado (advisory lock)

Se uma execução anterior falhou e não liberou o lock, o advisory lock do PostgreSQL é liberado automaticamente quando a conexão é fechada. Se o processo ainda estiver vivo, encerre-o manualmente.

### Problema: Credenciais expostas

Se o `.env` foi commitado por acidente:
1. **Rotacione imediatamente** todas as credenciais contidas nele.
2. Remova o arquivo do rastreamento: `git rm --cached .env`.
3. Adicione `.env` ao `.gitignore`.
4. Considere limpar o histórico do Git (`git filter-repo` ou similar) se o repositório for público.

---

## Migrações

### Aplicar migrações pendentes

```bash
python infra/migrate.py
```

### Listar pendentes sem aplicar

```bash
python infra/migrate.py --verificar
```

### Backup antes de migração destrutiva

```bash
pg_dump -h localhost -p 5432 -U usuario -d hub_vagas -f backup_antes_da_migracao.sql
```

### Migração já aplicada foi modificada

O migrador detecta alterações em migrações já aplicadas (via checksum) e aborta. Crie uma nova migração em vez de modificar uma existente.

---

## Power BI (bi_reader)

### Criar a role

```sql
CREATE ROLE bi_reader LOGIN password '<senha-fora-do-repo>';
GRANT CONNECT ON DATABASE hub_vagas TO bi_reader;
GRANT USAGE ON SCHEMA gold TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO bi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO bi_reader;
```

O dbt recria as tabelas Gold a cada build; `dbt_project.yml` declara `+grants: select: ['bi_reader']` para reautomatizar os grants.

### Conectar no Power BI

1. Obter Dados → PostgreSQL database
2. Informe host, porta, database, usuário `bi_reader` e senha
3. Selecione tabelas do schema `gold`

---

## Logs

Os logs ficam em `logs/pipeline.log` com rotação a cada 5 MB (3 backups).
