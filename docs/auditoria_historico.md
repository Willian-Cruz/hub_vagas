# Auditoria do Histórico do Repositório

**Data:** 2026-11-19
**Escopo:** `git log --all --diff-filter=A --name-only --pretty=format:` (arquivos adicionados ao longo do histórico)
**Filtro:** arquivos `.sql`, `.zip`, `.dump`, `.gz`, `.html` (excluindo `venv/`)

---

## Arquivos Problemáticos Encontrados no Histórico

### 1. `app/infojobs_page1.html`
- **Tipo:** HTML grande (página completa do InfoJobs)
- **Risco:** Pode conter dados sensíveis de sessão, tokens, PII de vagas reais
- **Ação recomendada:** `git filter-repo --path app/infojobs_page1.html --invert-paths` + rotacionar credenciais se houver tokens

### 2. `logs/query_log.sql`
- **Tipo:** Log de queries SQL
- **Risco:** Pode conter dados sensíveis, estrutura de tabelas, valores reais
- **Ação recomendada:** `git filter-repo --path logs/query_log.sql --invert-paths`

### 3. `debug_html.html`
- **Tipo:** HTML de debug
- **Risco:** Pode conter páginas completas com dados reais
- **Ação recomendada:** `git filter-repo --path debug_html.html --invert-paths`

### 4. `dashboard/dashboard.html`
- **Tipo:** Dashboard HTML (GitHub Pages antigo)
- **Risco:** Baixo (público), mas não deve estar no histórico do código
- **Ação recomendada:** `git filter-repo --path dashboard/dashboard.html --invert-paths`

---

## Arquivos Legítimos (não requerem ação)

### Migrações SQL (`infra/migrations/`)
- 000 a 010 - migrações de schema legítimas

### Modelos e testes dbt (`dbt/`)
- Models, macros, tests - parte do projeto

### Fixtures de teste (`app/tests/fixtures/`)
- `catho_cards_2026_11.html`, `infojobs_cards_2026_11.html`, `infojobs_cards.html`, `vagas_com_cards.html`
- **Nota:** Testados em `test_fixtures_seguranca.py` - sem padrões sensíveis detectados

---

## Varredura de Segredos (gitleaks)

Executar:
```bash
gitleaks detect --source . --verbose --redact
```

**Resultado esperado:** 0 segredos (baseline limpo em `.secrets.baseline`)

---

## Comandos para Limpeza (executar pelo humano)

```bash
# Backup antes de reescrever histórico
git bundle create hub_vagas_backup.bundle --all

# Remover arquivos sensíveis do histórico
git filter-repo --path app/infojobs_page1.html --invert-paths
git filter-repo --path logs/query_log.sql --invert-paths
git filter-repo --path debug_html.html --invert-paths
git filter-repo --path dashboard/dashboard.html --invert-paths

# Forçar push (requer coordenação da equipe)
git push --force-with-lease origin --all
git push --force-with-lease origin --tags

# Rotacionar credenciais que possam ter vazado
# - Senhas de banco
# - Tokens de API
# - Chaves SSH
# - Webhooks
```

---

## Observações

- O diretório `venv/` foi commitado no passado (milhares de arquivos). Recomenda-se adicionar `venv/` ao `.gitignore` (já feito) e, opcionalmente, limpar do histórico com `git filter-repo --path venv/ --invert-paths`.
- A limpeza do histórico **reescreve SHA dos commits** - coordenar com a equipe antes de executar.
- Após limpeza, regenerar `.secrets.baseline` com `detect-secrets scan > .secrets.baseline`.