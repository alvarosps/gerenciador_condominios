# Plano P0.1 — Incidente: purga de dados/segredos do git + rotação + hooks + higiene do repo

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P0 (INCIDENTE — fazer ANTES de tudo) · **Branch sugerida:** `chore/security-incident-git-purge` · **Depende de:** nenhum

## Objetivo

Conter e remediar o vazamento de dados pessoais reais (CPF/RG/telefone de inquilinos, hashes pbkdf2 de admins e tokens OAuth) que estao commitados e publicados no GitHub (`git@github.com:alvarosps/gerenciador_condominios.git`). O plano remove os blobs do working tree e de TODO o historico via `git filter-repo`, rotaciona os segredos expostos (que devem ser tratados como comprometidos), tampa os buracos do `.gitignore`, destrava o enforcement de hooks que hoje e inerte (`core.hooksPath` aponta para `.git/hooks` vazio), alinha a documentacao (CLAUDE.md/security.md afirmam enforcement que nao existe) e remove arquivos mortos/perigosos da raiz. E majoritariamente operacional/ops; nao introduz mudanca de comportamento de runtime.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| CRITICO | Dump SQL com PII + 31 `socialaccount_socialtoken` + hashes pbkdf2 commitado | `local_backup.sql` (630 KB, tracked) | `git rm --cached` + purga do historico + rotacao de tokens/senhas |
| CRITICO | Dump JSON do banco com PII real | `backup_condominio_20260402.json` (1.6 MB, tracked) | purgar do historico |
| CRITICO | Dump binario pg_dump custom com PII | `backup_condominio_20260402_162358.dump` (323 KB, tracked) | purgar do historico |
| CRITICO | 4 backups SQL de janeiro com PII | `backups/backup_condominio_20260119_*.sql` (4 arquivos, tracked apesar de `/backups/` no .gitignore) | `git rm -r --cached backups/` + purgar do historico |
| CRITICO | 22 fixtures JSON com PII (inclui `user.json` com pbkdf2, `tenant.json` com 60 CPFs) | `backup_json/*.json` | purgar do historico (dir inteiro) |
| CRITICO | 27 PDFs de contrato com PII (CPF/RG/endereco de inquilinos) | `contracts/836/*.pdf` (19), `contracts/850/*.pdf` (8) | purgar do historico + ignorar `/contracts/` (exceto template paths) |
| CRITICO | PDF de reajuste com nome/valor real | `Notificacao_Reajuste_Kitnet_205.pdf` (raiz) | purgar do historico + deletar script gerador |
| ALTO | `.gitignore` sem `*.dump`, `*.sql` raiz, `backup_json/`, `/contracts/` inteiro; `.env` duplicado | `.gitignore:35` e `:55` (duplicata); falta de regras | corrigir `.gitignore` (1 secao de backups + remover duplicata) |
| ALTO | `.superpowers/` runtime tracked (incl. `.server.pid`, mockups HTML) | 23 arquivos `.superpowers/**` (apesar de `.superpowers/` no .gitignore) | `git rm -r --cached .superpowers/` |
| ALTO | Nenhum hook git instalado — `core.hooksPath` aponta para `.git/hooks` vazio | `git config core.hooksPath` = `.git/hooks` (so `.sample`); `.pre-commit-config.yaml` e `frontend/.husky/pre-commit` inertes | instalar `pre-commit` (raiz) como mecanismo unico; husky cobre so frontend via lint-staged |
| ALTO | CLAUDE.md/security.md afirmam enforcement inexistente | `CLAUDE.md:96-97`, `.claude/rules/security.md:22` (`detect-private-key pre-commit hook is active`) | corrigir docs apos instalar hooks de verdade |
| MEDIO | Script morto na raiz: `pip install` em runtime + PII real + dep `fpdf2` fora dos requirements + per-file-ignore S603 | `generate_notice_pdf.py:5-13,32-60`; `pyproject.toml:251-252` | deletar script + PDF + a linha de per-file-ignore |
| MEDIO | SQL morto/perigoso (24 KB de DDL/DML solto) | `database_migration_scripts.sql` | deletar |
| MEDIO | Importador one-off morto | `scripts/import_caixa_abril.py` | deletar |
| MEDIO | Script de metricas com `flake8`/`pylint`/`pip install` (stack abandonada — Ruff substitui) | `scripts/generate_metrics.py:9-10,84-86,162-165` | deletar + remover permissao em `.claude/settings.json:21` |
| MEDIO | Stack Docker/nginx/deploy morta e quebrada (nao usada em prod: Vercel+Render+Supabase) | `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `nginx/conf.d/condominios.conf`, `nginx/nginx.conf`, `scripts/deploy.sh` | deletar (avaliar antes) |

## Abordagem técnica

> **PRE-REQUISITO ABSOLUTO (executar antes de qualquer `git rm`/purga):** criar um clone-espelho de seguranca FORA do repo para nao perder historico recuperavel e ter backup dos blobs:
> `git clone --mirror git@github.com:alvarosps/gerenciador_condominios.git ../gerenciador_condominios-incident-mirror.git`
> Guardar esse espelho offline. Ele NAO sera force-pushed.

### Passo 0 — Branch e inventario
1. `git switch -c chore/security-incident-git-purge` a partir de `master`.
2. Gerar e versionar (no commit do plano) o inventario exato dos paths sensiveis para o `--paths-from-file` do filter-repo. Lista canonica (78 arquivos tracked, confirmada via `git ls-files`):
   - `local_backup.sql`
   - `backup_condominio_20260402.json`
   - `backup_condominio_20260402_162358.dump`
   - `Notificacao_Reajuste_Kitnet_205.pdf`
   - `backups/` (4 `.sql`)
   - `backup_json/` (22 `.json`)
   - `contracts/836/` (19 `.pdf`) e `contracts/850/` (8 `.pdf`)
   - `database_migration_scripts.sql`

### Passo 1 — Tampar o `.gitignore` ANTES de remover (evita re-track acidental)
Editar `.gitignore`:
1. Remover a linha duplicada `.env` (existe em `:35` e `:55`) — manter apenas uma (mover/garantir junto de `.env*.local` em `:34`).
2. Substituir a regra estreita `/contracts/payment_proofs/` (`:64-65`) por ignore de TODO o conteudo gerado de `/contracts/` mantendo a estrutura versionavel:
   ```gitignore
   # Generated contract PDFs + uploaded payment proofs (PII) — never commit
   /contracts/**/*.pdf
   /contracts/payment_proofs/
   ```
   (assim `contracts/{building}/` permanece como diretorio de saida runtime sem versionar os PDFs).
3. Ampliar a secao "Database backups" (`:68-69`) para cobrir todos os formatos e o dir de fixtures:
   ```gitignore
   # Database backups & dumps (PII) — never commit
   /backups/
   /backup_json/
   *.dump
   /*.sql
   /*.json.gz
   ```
   Observacao: usar `/*.sql` (apenas raiz) para nao colidir com SQL legitimo dentro de `core/migrations` ou seeds; `database_migration_scripts.sql` (raiz) sera deletado no Passo 5, mas a regra impede recriacao. NAO usar `*.json` global (quebraria `package.json`, `tsconfig.json`, `.mcp.json`, seeds em `scripts/data/`).
4. Adicionar ignore explicito do PDF de reajuste na raiz: `/Notificacao_*.pdf`.

### Passo 2 — `git rm --cached` (untrack sem deletar do disco onde fizer sentido)
Remover do indice mantendo no working tree apenas o que e legitimo localmente (backups locais o dono pode querer manter em disco, mas FORA do git):
- `git rm -r --cached backups/ backup_json/ contracts/836/ contracts/850/ .superpowers/`
- `git rm --cached local_backup.sql backup_condominio_20260402.json backup_condominio_20260402_162358.dump Notificacao_Reajuste_Kitnet_205.pdf database_migration_scripts.sql`
- Mover os dumps locais para fora do repo (o destino canonico ja existe — `scripts/backup_db.py` grava em `/backups/`, que e ignorado): mover `local_backup.sql`, `backup_condominio_*.json/.dump` para `../condominio-backups-local/` no disco (operacao de filesystem, nao git).

Commitar este passo isolado: `chore(security): untrack DB dumps, contract PDFs, backup_json, .superpowers`.

### Passo 3 — Reescrita de historico (purga dos blobs de TODO o historico)
Ferramenta: **`git filter-repo`** (NAO instalado — `git filter-repo --version` falha; instalar via `uv tool install git-filter-repo` ou `pipx install git-filter-repo`). BFG e alternativa, mas filter-repo e o recomendado oficial e suporta `--paths-from-file`.
1. Escrever `incident-purge-paths.txt` (um path/glob por linha) com a lista do Passo 0. Para diretorios usar `glob:contracts/836/**`, `glob:backup_json/**`, etc.; filter-repo aceita `glob:` e `literal:`.
2. Executar (em um clone fresco do mirror para nao corromper o repo de trabalho):
   `git filter-repo --invert-paths --paths-from-file incident-purge-paths.txt`
3. Conferir que os blobs sumiram: `git log --all --oneline -- local_backup.sql` deve retornar vazio; idem para um PDF de contrato e `backup_json/user.json`.
4. Reaplicar o remote (filter-repo o remove por seguranca): `git remote add origin git@github.com:alvarosps/gerenciador_condominios.git`.

### Passo 4 — Force-push e comunicacao
1. `git push origin --force --all` e `git push origin --force --tags`.
2. **Avisar explicitamente** (handoff): este e o unico repo e o unico dev (`alvarosps`), entao nao ha PRs abertos a reescrever; mas QUALQUER clone/fork/CI cache anterior ainda contem os blobs. Acoes pos-push:
   - Pedir ao GitHub para invalidar caches de blobs sensiveis (Support) ou, no minimo, considerar os dados ja vazados (assumir comprometimento — daí a rotacao do Passo abaixo).
   - Re-clonar localmente do repo reescrito (descartar clones antigos que mantem os blobs no reflog).
   - Verificar Vercel/Render: se algum deploy fez checkout do historico, os blobs podem estar em artefatos — checar build logs nao e necessario porque os PDFs nunca eram servidos, mas confirmar que nenhum job os exporta.

### Passo 5 — ROTACAO de segredos (tratar tudo exposto como comprometido)
Os dumps continham material sensivel de auth; rotacionar mesmo apos a purga, pois ja estiveram publicos:
1. **`SECRET_KEY`** (`settings.py:29` `config("SECRET_KEY")`; tambem usado como `SIGNING_KEY` do JWT em `:310`): gerar novo (`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`), atualizar no `.env` local e nas env vars do Render (backend) e Vercel (se aplicavel). **Efeito colateral conhecido:** trocar `SECRET_KEY` invalida todos os JWT em circulacao (assinados com a chave antiga) — logout forcado de todos os usuarios web+mobile. Aceitavel e desejado (os tokens vazaram).
2. **`GOOGLE_CLIENT_SECRET`** (`settings.py:381`): rotacionar no Google Cloud Console (gerar novo secret do OAuth client, revogar o antigo), atualizar env vars. `GOOGLE_CLIENT_ID` nao e segredo, mas revogar o secret invalida o par.
3. **Senhas de admin** (hashes pbkdf2 vazaram em `backup_json/user.json` e `local_backup.sql`): forcar reset de senha de TODOS os usuarios `is_staff`/`is_superuser` no banco de prod (Supabase). Como o login admin web e via Google allowlist (`ADMIN_GOOGLE_EMAILS`), o risco principal e o admin Django (`/admin`) com senha local — resetar via `manage.py changepassword` em prod ou invalidar setando senha inutilizavel para contas nao usadas.
4. **Tokens OAuth** (`socialaccount_socialtoken`, 31 linhas no dump + os `OAuthExchangeCode` persistidos): revogar/limpar. Executar em prod, sob backup previo:
   `python scripts/backup_db.py` (backup) -> deletar linhas de `socialaccount_socialtoken` e `core_oauthexchangecode` via SQL parametrizado/ORM. A rotacao do `GOOGLE_CLIENT_SECRET` ja torna refresh tokens antigos inutilizaveis, mas a limpeza fecha a janela.

### Passo 6 — Instalar mecanismo unico de hooks e destravar enforcement
Diagnostico: `core.hooksPath` = `.git/hooks` (so arquivos `.sample`); `.pre-commit-config.yaml` existe e e completo (trailing-whitespace, **check-added-large-files maxkb=1000**, **detect-private-key**, ruff, ruff-format, mypy) mas nunca foi instalado; `frontend/.husky/pre-commit` (lint-staged + type-check) tambem nao roda porque o `core.hooksPath` aponta pro dir vazio e o husky escreveria em `.husky/_`.
Decisao (KISS, mecanismo unico na raiz): **adotar `pre-commit` da raiz como gerenciador de hooks de todo o repo** e fazer o husky/frontend ser chamado por ele, evitando dois gerenciadores disputando `core.hooksPath`.
1. Adicionar ao `.pre-commit-config.yaml` um hook local que roda o gate do frontend nos arquivos `frontend/**`:
   ```yaml
     - repo: local
       hooks:
         - id: frontend-lint-staged
           name: frontend lint-staged
           entry: bash -c 'cd frontend && npx lint-staged'
           language: system
           files: ^frontend/.*\.(ts|tsx)$
           pass_filenames: false
   ```
2. Instalar: `pre-commit install` (isso reescreve `.git/hooks/pre-commit` para invocar o pre-commit — resolvendo o `core.hooksPath` vazio sem alterar a config de hooksPath).
3. Remover o `frontend/.husky/pre-commit` e o script `"prepare": "husky"` de `frontend/package.json:19` (husky deixa de ser o gerenciador; o `lint-staged` config em `frontend/package.json:21` permanece, agora invocado pelo pre-commit). Remover `husky` de `devDependencies` (`frontend/package.json:110`).
4. Validar com um commit de teste (ver TDD): tentar commitar um arquivo >1000 KB e um arquivo com chave privada fake → o commit DEVE ser bloqueado.

### Passo 7 — Corrigir documentacao (alinhar com a realidade pos-instalacao)
1. `.claude/rules/security.md:22`: a afirmacao "`detect-private-key` pre-commit hook is active" passa a ser verdadeira apos Passo 6 — manter, mas adicionar nota de que o enforcement exige `pre-commit install` (documentar no setup).
2. `CLAUDE.md:96-97`: as frases "enforced via pre-commit" e "husky + lint-staged" agora descrevem o estado real (frontend rodando via hook local do pre-commit); atualizar a `:97` para refletir que o frontend roda via pre-commit (nao mais husky direto). Adicionar uma linha no setup (`scripts/setup_windows` ou README) instruindo `pre-commit install` no clone.
3. `frontend/CLAUDE.md` (secao "Git Hooks"): atualizar de "husky + lint-staged ... no pre-commit" para "lint-staged via pre-commit raiz".

### Passo 8 — Deletar arquivos mortos (avaliados)
1. `generate_notice_pdf.py` (raiz): script one-off, sem nenhum importador (grep so encontra referencias em docs/config), faz `pip install fpdf2` em runtime (`:5-13`) e embute PII real (`:32-60`). **Deletar.** Remover tambem:
   - `pyproject.toml:251-252` (o `[tool.ruff.lint.per-file-ignores]` `"generate_notice_pdf.py" = ["S603"]` fica orfao).
   - `fpdf2` nao esta em `requirements*.txt` nem `pyproject.toml` (confirmado) — nada a remover de deps, apenas o script.
2. `database_migration_scripts.sql` (raiz, 24 KB): DDL/DML solto, fora do fluxo de migrations sequenciais do Django — perigoso e morto. **Deletar.**
3. `scripts/import_caixa_abril.py`: importador one-off de abril, sem agendamento nem importador. **Deletar.**
4. `scripts/generate_metrics.py`: roda `flake8`/`pylint`/`pip install` (`:9-10,84-86,162-165`) — stack abandonada (Ruff+mypy+pyright a substituem; ja documentado em CLAUDE.md). **Deletar** e remover a permissao `"Bash(python scripts/generate_metrics.py:*)"` em `.claude/settings.json:21`.
5. Stack Docker/nginx/deploy: prod roda Vercel(frontend)+Render(backend)+Supabase(db) — Docker/nginx nao sao usados. **Avaliar e deletar** `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `nginx/conf.d/condominios.conf`, `nginx/nginx.conf`, `scripts/deploy.sh`. (Avaliacao = confirmar com o dono que nenhum ambiente local depende deles; se houver duvida, mover para um branch/tag arquivado em vez de apagar — mas a recomendacao e deletar.)

## Arquivos a criar / modificar

- `.gitignore` — remover `.env` duplicado (`:35`/`:55`); ampliar ignore de contracts/backups/dumps; adicionar `/backup_json/`, `*.dump`, `/*.sql`, `/Notificacao_*.pdf`.
- `.pre-commit-config.yaml` — adicionar hook local `frontend-lint-staged`.
- `frontend/package.json` — remover script `prepare: husky` (`:19`) e dep `husky` (`:110`); manter `lint-staged` config (`:21`).
- `frontend/.husky/pre-commit` — **deletar** (e o dir `.husky/` se vazio).
- `pyproject.toml` — remover per-file-ignore `generate_notice_pdf.py` (`:251-252`).
- `.claude/settings.json` — remover permissao `generate_metrics.py` (`:21`).
- `CLAUDE.md` — atualizar `:96-97` (hook reality); adicionar instrucao `pre-commit install` no setup.
- `frontend/CLAUDE.md` — atualizar secao "Git Hooks".
- `.claude/rules/security.md` — nota sobre `pre-commit install` no `:22`.
- **Deletar (working tree + indice):** `generate_notice_pdf.py`, `Notificacao_Reajuste_Kitnet_205.pdf`, `database_migration_scripts.sql`, `scripts/import_caixa_abril.py`, `scripts/generate_metrics.py`, `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `nginx/conf.d/condominios.conf`, `nginx/nginx.conf`, `scripts/deploy.sh`.
- **Untrack (git rm --cached, manter/mover em disco):** `local_backup.sql`, `backup_condominio_20260402.json`, `backup_condominio_20260402_162358.dump`, `backups/`, `backup_json/`, `contracts/836/`, `contracts/850/`, `.superpowers/`.
- **Criar (auxiliares de incidente, NAO versionar):** `incident-purge-paths.txt` (input do filter-repo; adicionar ao `.gitignore` ou deletar apos uso).
- Sem arquivos de teste de codigo (plano operacional) — verificacoes sao via comandos git/hook (ver TDD).

## TDD — cenários de teste

Plano operacional: as "verificacoes" sao checagens binarias pos-execucao, nao testes pytest/vitest.

- `historico_limpo_local_backup` — `git log --all --oneline -- local_backup.sql` retorna vazio (blob purgado).
- `historico_limpo_pdf_contrato` — `git log --all --oneline -- contracts/836/contract_apto_113_1.pdf` vazio.
- `historico_limpo_user_json` — `git log --all --oneline -- backup_json/user.json` vazio (hashes pbkdf2 sumiram).
- `historico_limpo_socialtoken` — `git grep -I 'socialaccount_socialtoken' $(git rev-list --all) -- '*.sql'` sem matches (tokens fora do historico).
- `ls_files_sem_pii` — `git ls-files | grep -iE '^(backups/|backup_json/|contracts/8|local_backup|backup_condominio|Notificacao_)'` retorna vazio.
- `ls_files_sem_superpowers` — `git ls-files | grep '.superpowers/'` vazio.
- `gitignore_sem_env_duplicado` — `grep -c '^.env$' .gitignore` == 1.
- `gitignore_cobre_dumps` — criar `teste.dump`, `teste.sql` na raiz e `backup_json/x.json` → `git status --porcelain` nao os lista (ignorados).
- `gitignore_nao_quebra_legitimos` — `git check-ignore frontend/package.json scripts/data/financial_data_template.json .mcp.json` retorna codigo !=0 (NAO ignorados — regressao de `/*.sql`/`/*.json` ser raiz-only e nao `*.json` global).
- `hook_bloqueia_arquivo_grande` — `dd` de um arquivo de 2 MB, `git add` + `git commit` → bloqueado por `check-added-large-files` (maxkb=1000).
- `hook_bloqueia_chave_privada` — commitar um arquivo com `-----BEGIN RSA PRIVATE KEY-----` fake → bloqueado por `detect-private-key`.
- `hook_frontend_roda` — editar um `frontend/**/*.tsx` com erro de lint → commit bloqueado pelo hook local `frontend-lint-staged`.
- `ruff_ainda_passa` — `ruff check && ruff format --check` verde apos remover `generate_notice_pdf.py` e seu per-file-ignore (sem regra orfa apontando para arquivo inexistente).
- `pyright_mypy_ainda_passam` — `mypy core/ && pyright` verdes (nenhum dos arquivos deletados era importado).
- `scripts_data_intactos` — seeds `scripts/data/*.json` continuam tracked (NAO sao backups; regras de ignore nao os pegam).

## Migrations / dados

N/A para mudanca de schema. **Correcao de dado vivo (Passo 5):** limpeza de `socialaccount_socialtoken` e `core_oauthexchangecode` em PROD (Supabase) e reset de senhas admin — operacoes de dados, nao migration. **Backup obrigatorio antes:** `python scripts/backup_db.py` (e mover o dump resultante para fora do repo — `/backups/` ja e ignorado pelo `.gitignore` corrigido). Nenhuma tabela nova → nenhuma alteracao de RLS necessaria.

## Constraints (o que NÃO fazer)

- NAO commitar o clone-mirror de seguranca nem `incident-purge-paths.txt` no repo (sao artefatos do incidente).
- NAO rodar `migrate` apos a limpeza de dados em prod (a limpeza e `DELETE`/reset pontual; o schema nao muda — alinhado a regra de sync prod->local sem migrate).
- NAO usar `*.json` global no `.gitignore` (quebraria `package.json`, `tsconfig.json`, `.mcp.json`, seeds em `scripts/data/`); restringir a `/backup_json/` + dumps de raiz.
- NAO manter dois gerenciadores de hooks: husky e removido como gerenciador; `pre-commit` (raiz) e o unico, invocando lint-staged via hook local.
- NAO usar `# noqa`/`# type: ignore`/`eslint-disable` para silenciar a regra orfa de per-file-ignore — remover a regra de verdade.
- NAO tocar no modulo financeiro legado nem no app `finances/` — este plano e so incidente/higiene de repo.
- NAO arquivar a stack Docker apagando "por garantia" sem a avaliacao: confirmar que nenhum ambiente local depende dela antes de deletar (se houver duvida, tag de arquivo).
- NAO esquecer de re-clonar localmente apos o force-push (clones antigos retem os blobs no reflog).

## Critérios de aceite (binários)

- [ ] Clone-mirror de seguranca criado fora do repo antes de qualquer purga.
- [ ] `git ls-files` nao retorna nenhum dump (`.sql`/`.dump`/`.json` de backup), PDF de contrato, `backup_json/`, `backups/`, `.superpowers/` ou `Notificacao_*.pdf`.
- [ ] Historico (`--all`) sem os blobs: 5 checagens `git log --oneline -- <path>` vazias (local_backup, pdf contrato, user.json, dump, backup_condominio json).
- [ ] `git grep socialaccount_socialtoken` sobre todo o historico sem matches.
- [ ] Force-push concluido em `--all` e `--tags`; repo re-clonado limpo.
- [ ] `SECRET_KEY`, `GOOGLE_CLIENT_SECRET` rotacionados (env local + Render/Vercel); senhas admin resetadas; `socialaccount_socialtoken`/`core_oauthexchangecode` limpos em prod (sob backup).
- [ ] `.gitignore` com `.env` unico, cobrindo `*.dump`, `/*.sql`, `/backup_json/`, `/contracts/**/*.pdf`, `/Notificacao_*.pdf`; `git check-ignore` NAO pega `package.json`/`tsconfig.json`/`scripts/data/*.json`.
- [ ] `pre-commit install` feito; commit de arquivo >1 MB e de chave privada fake sao bloqueados; hook frontend roda em `*.tsx`.
- [ ] `frontend/.husky/pre-commit` removido; `husky` fora do `package.json`; `lint-staged` config preservado.
- [ ] CLAUDE.md (`:96-97`), `frontend/CLAUDE.md`, `.claude/rules/security.md:22` refletem o enforcement real + instrucao `pre-commit install`.
- [ ] Arquivos mortos deletados; `pyproject.toml` sem per-file-ignore orfao; `.claude/settings.json` sem permissao de `generate_metrics.py`.
- [ ] `ruff check && ruff format --check && mypy core/ && pyright` verdes; `cd frontend && npm run lint && npm run type-check` verdes.

## Gate de verificação

Escopado (arquivos editados) + regressao dirigida:

```bash
# Higiene git (escopado ao incidente)
git ls-files | grep -iE '^(backups/|backup_json/|contracts/8|local_backup|backup_condominio|Notificacao_|.superpowers/)' && echo FAIL || echo OK
git log --all --oneline -- local_backup.sql backup_json/user.json contracts/836/contract_apto_113_1.pdf
git check-ignore -v frontend/package.json scripts/data/financial_data_template.json .mcp.json   # esperado: exit !=0

# Hooks
pre-commit install && pre-commit run --all-files

# Backend (regressao dirigida nos arquivos tocados: pyproject, settings nao mudou de logica)
ruff check && ruff format --check && mypy core/ && pyright

# Frontend (regressao do package.json/husky removido)
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

A suite Python completa NAO e bloqueio (flakiness pre-existente de xdist/Redis). Zero erros E zero warnings nos comandos acima.

## Handoff

Commits sugeridos (sequenciais na branch `chore/security-incident-git-purge`):
1. `chore(security): tighten .gitignore (dumps, contracts, backup_json; drop duplicate .env)`
2. `chore(security): untrack DB dumps, contract PDFs, backup_json, .superpowers`
3. `chore(repo): remove dead scripts (notice/metrics/caixa) + Docker/nginx/deploy stack`
4. `chore(hooks): install pre-commit as single hook manager; route frontend lint-staged via local hook`
5. `docs(security): align CLAUDE.md/security.md with real hook enforcement`

Mensagem de commit (template, com co-autor exigido):
```
chore(security): purge committed DB dumps/PII/OAuth tokens from git history

Remove from working tree and full history: DB dumps (local_backup.sql,
backup_condominio_*), 27 contract PDFs, backup_json/ fixtures, reajuste PDF.
Rotate SECRET_KEY, GOOGLE_CLIENT_SECRET, admin passwords, OAuth tokens.
Tighten .gitignore, install pre-commit hooks, delete dead scripts.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

**A reescrita de historico e o force-push sao operacoes manuais do dono** (envolvem credenciais do GitHub e Render/Vercel/Supabase) — o agente prepara branch/`.gitignore`/hooks/deleções e o `incident-purge-paths.txt`, mas a execucao do `git filter-repo` + force-push + rotacao de segredos em prod deve ser feita/confirmada pelo dono.

Atualizar estado: registrar na MEMORY do projeto que o incidente foi remediado (purga + rotacao + hooks instalados), substituindo a expectativa de enforcement inexistente. O **proximo plano (P1+) assume:** historico limpo, hooks ativos bloqueando segredos/arquivos grandes, e que nenhum backup/dump volte a ser commitado (backups vivem so em `/backups/` ignorado, gerados por `scripts/backup_db.py`).
