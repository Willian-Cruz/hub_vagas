# Contribuindo com o Hub Vagas

Obrigado por se interessar em contribuir! Este documento explica como propor
mudanças, reportar problemas e enviar pull requests.

---

## 1. Antes de começar

- Leia o [ARCHITECTURE.md](./ARCHITECTURE.md) para entender a arquitetura de dados.
- Leia o [README.md](./README.md) para saber como executar o projeto localmente.
- Verifique se já existe uma issue ou PR sobre o assunto.

---

## 2. Como enviar mudanças

### 2.1 Crie uma branch

Use uma branch descritiva a partir da `main`:

```bash
git checkout -b fix/M01-seguranca-env
git checkout -b feat/M05-camadas-dados
git checkout -b docs/M07-contribuindo
```

### 2.2 Faça as alterações

- Siga o estilo de código existente (ruff está configurado).
- Adicione ou atualize testes quando modificar código Python ou SQL dbt.
- Atualize a documentação relevante (README, ARCHITECTURE.md, docs/).

### 2.3 Execute as verificações locais

```bash
# Lint
ruff check app/

# Testes unitários (sem PostgreSQL)
cd app
pytest tests/ -m "not integration" -q --tb=short

# dbt build (requer PostgreSQL local)
python app/transform.py
```

### 2.4 Commit

Use mensagens de commit no formato convencional:

```
feat(M05): adicionar ARCHITECTURE.md com camadas de dados
fix(M01): remover .env do rastreamento Git
docs(M07): adicionar CONTRIBUTING.md
```

### 2.5 Abra um Pull Request

- Abra o PR contra a branch `main`.
- Descreva o que foi alterado e por quê.
- Vincule issues relacionadas, se houver.
- Aguarde a aprovação dos checks do CI antes de fazer merge.

---

## 3. Regras do repositório

- **Nunca commite credenciais.** O arquivo `.env` está no `.gitignore` e não
  deve ser versionado. Se você precisar de credenciais para testes locais,
  copie `.env.example` para `.env` e preencha com valores locais.
- **Nunca comite arquivos grandes** (zips, backups, `.pyc`, HTML salvo do navegador).
- **Migrações SQL** que apaguem dados exigem backup documentado antes de aplicar.
- **Tabelas dbt** são recriadas a cada build; não altere manualmente no banco.

---

## 4. Reportando problemas

Abra uma issue com:
- Descrição do problema ou solicitação.
- Passos para reproduzir (se for bug).
- Comportamento esperado vs. observado.
- Ambiente (SO, versão do Python, PostgreSQL).
