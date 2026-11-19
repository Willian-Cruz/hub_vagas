# Proteção da Branch `main` — Hub Vagas

> **IMPORTANTE:** Não altere configurações do GitHub sem autorização explícita.
> Este documento serve como recomendação para ser aplicada manualmente via UI do GitHub
> (Settings → Branches → Branch protection rules) ou via `gh api`.

---

## Proteções Recomendadas para `main`

| Proteção | Valor | Justificativa |
|----------|-------|---------------|
| **Exigir Pull Request** | ✅ Habilitado | Impede pushes diretos; garante revisão |
| **Exigir aprovações** | 1 revisor mínimo | Garante code review |
| **Exigir checks obrigatórios** | ✅ Ver abaixo | Bloqueia merge se CI falhar |
| **Exigir resolução de conversas** | ✅ Habilitado | Impede merge com discussões pendentes |
| **Impedir force push** | ✅ Habilitado | Protege histórico |
| **Impedir exclusão da branch** | ✅ Habilitado | Protege branch principal |
| **Incluir administradores** | ✅ Habilitado | Regras valem para todos |
| **Exigir assinatura de commits** | Opcional | Se política da organização exigir |

---

## Checks Obrigatórios (Status Checks)

Os seguintes jobs do workflow **`CI Hub Vagas`** (arquivo `.github/workflows/tests.yml`) devem ser marcados como **Required** na configuração de Branch Protection:

| Job ID | Display Name | Descrição |
|--------|--------------|-----------|
| `deps` | **Validacao de dependencias** | Verifica se `requirements.txt` e `requirements-dev.txt` estão sincronizados com `.in` via `pip-compile` |
| `lint` | **Lint (ruff)** | Executa `ruff check app/` — estilo, imports, bugs |
| `test` | **Testes unitarios** | `pytest app/tests/ -m "not integration"` — 323 testes |
| `integration` | **Testes de integracao** | `pytest app/tests/integration/ -m integration` — PostgreSQL real, 7 cenários E2E (A-G), migrations |
| `dbt-build` | **dbt build (PostgreSQL)** | `dbt build` completo — models, tests, seeds, snapshots |
| `security` | **Seguranca (detecao de secrets)** | `detect-secrets scan --baseline .secrets.baseline` |
| `pip-audit` | **Scanner de vulnerabilidades (pip-audit)** | Audita `requirements.txt` e `requirements-dev.txt` |

### Ordem de Execução (dependências)

```
deps (sem deps)
  ├── lint (precisa deps)
  ├── test (precisa deps)
  ├── integration (precisa deps)
  ├── security (precisa deps)
  └── pip-audit (precisa deps)
  └── dbt-build (precisa test)
```

> **Nota:** O job `dbt-build` roda apenas após `test` passar (via `needs: test`).

---

## Como Configurar via GitHub CLI (`gh`)

```bash
# 1. Ver regras atuais
gh api repos/Willian-Cruz/hub_vagas/branches/main/protection

# 2. Aplicar proteções (exemplo - ajustar owner/repo)
gh api --method PUT repos/Willian-Cruz/hub_vagas/branches/main/protection \
  --field required_status_checks='{"strict":true,"contexts":["Validacao de dependencias","Lint (ruff)","Testes unitarios","Testes de integracao","dbt build (PostgreSQL)","Seguranca (detecao de secrets)","Scanner de vulnerabilidades (pip-audit)"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_linear_history=false \
  --field required_conversation_resolution=true
```

> **Atenção:** Os nomes em `contexts` devem corresponder **exatamente** aos `name:` dos jobs no workflow YAML.

---

## Verificação Pós-Configuração

Após aplicar, teste:

1. Crie uma branch, faça alteração, abra PR
2. Confirme que **todos os 7 checks aparecem** na aba "Checks" do PR
3. Tente fazer merge sem aprovação → deve bloquear
4. Tente fazer merge com CI falhando → deve bloquear
5. Force push para `main` → deve bloquear (mesmo para admins)

---

## Referência: Nomes Exatos dos Jobs (do `.github/workflows/tests.yml`)

```yaml
jobs:
  deps:
    name: Validacao de dependencias
  lint:
    name: Lint (ruff)
  test:
    name: Testes unitarios
  integration:
    name: Testes de integracao
  dbt-build:
    name: dbt build (PostgreSQL)
  security:
    name: Seguranca (detecao de secrets)
  pip-audit:
    name: Scanner de vulnerabilidades (pip-audit)
```

Estes são os **7 checks obrigatórios** que devem estar verdes antes de qualquer merge na `main`.