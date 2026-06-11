# Plano P6.3 — CI, gates e higiene de build/deploy

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P6 · **Branch sugerida:** `chore/ci-and-build-hygiene` · **Depende de:** P0.1 (remove o stack Docker/nginx/deploy.sh morto e os scripts `generate_metrics`/`import_caixa_abril`; este plano referencia, NAO duplica essa remocao)

## Objetivo

Alinhar o pipeline de CI (`.github/workflows/ci.yml`) ao gate canonico de qualidade definido em `.claude/rules/coding-standards.md` (`ruff check . && ruff format --check . && mypy core/ condominios_manager/ finances/ && pyright && python -m pytest`), de forma que o app de producao `finances/` (hoje fora de ruff/mypy/bandit) seja efetivamente lintado, tipado e auditado, que `pyright` rode no CI, e que o job de seguranca deixe de ser decorativo. Em paralelo, corrigir a configuracao do ruff que classifica `finances` como third-party (isort agrupando errado) e eliminar a divergencia de versao-alvo de Python entre CI/mypy/ruff/pyright/runtime, escolhendo um alvo unico (3.14). O resultado e um CI que falha de verdade quando o codigo viola o gate, refletindo o ambiente real de producao (Postgres 17 do Supabase).

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO→MEDIO | CI nao lintea/tipa `finances/` — ruff e mypy so em `core/`+`condominios_manager/` | `.github/workflows/ci.yml:103-108` | `ruff check . && ruff format --check .` no repo; `mypy core/ condominios_manager/ finances/` |
| ALTO→MEDIO | `pyright` (gate obrigatorio) nao roda no CI | `.github/workflows/ci.yml:75-108` | Adicionar step de pyright no job `code-quality` |
| ALTO→MEDIO | Job `security` decorativo (`continue-on-error`) e `build-status` nao checa seu resultado | `.github/workflows/ci.yml:186,191,201-234` | Remover `continue-on-error`, falhar bandit/safety de verdade e incluir `security` em `build-status` |
| ALTO→MEDIO | `safety check` deprecated; bandit nao varre `finances/` | `.github/workflows/ci.yml:185,190` | `safety scan`; `bandit -r core/ condominios_manager/ finances/` |
| ALTO→MEDIO | `actions/checkout@v3` / `actions/setup-python@v4` desatualizados | `.github/workflows/ci.yml:30,33,80,83,118,147,169,171` | `checkout@v4` / `setup-python@v5` |
| ALTO→MEDIO | Service Postgres 15 no CI vs prod 17 / local 18 | `.github/workflows/ci.yml:16` | `image: postgres:17` |
| MEDIO | Ruff classifica `finances` como third-party (`src` e `known-first-party` sem `finances`/`tests`) | `pyproject.toml:122,209` | Adicionar `finances`/`tests` a `src` e `known-first-party` + `ruff check --fix .` mecanico |
| MEDIO | Versao-alvo de Python inconsistente (CI 3.12, mypy 3.12, ruff py313, pyright 3.14, rules 3.14) | `.github/workflows/ci.yml:32,35,82,85,171,174`; `pyproject.toml:9,120,285`; `pyrightconfig.json:2`; `render_build.sh` | Alvo unico 3.14: CI/mypy/ruff target/pyright/runtime Render |

## Abordagem técnica

Executar em DUAS metades, na ordem abaixo. A metade 1 (config ruff + reagrupamento mecanico) precisa vir ANTES de qualquer aperto do CI, senao o novo `ruff check .` quebra no proprio commit de config.

### Parte 1 — Config ruff first-party + commit mecanico de reagrupamento

1. Em `pyproject.toml`, na secao `[tool.ruff]` (linha 119), alterar `src = ["core", "condominios_manager"]` (linha 122) para `src = ["core", "condominios_manager", "finances", "tests"]`. Isso faz o isort do ruff resolver `finances`/`tests` como pacotes locais.
2. Em `[tool.ruff.lint.isort]` (linha 208), alterar `known-first-party = ["core", "condominios_manager"]` (linha 209) para `known-first-party = ["core", "condominios_manager", "finances", "tests"]`. `known-third-party = ["django", "rest_framework"]` (linha 210) e `section-order` (linha 211) permanecem.
3. Em `[tool.ruff]` (linha 120), alterar `target-version = "py313"` para `target-version = "py314"` (alinha ao alvo unico — ver Parte 3). Validar que ruff 0.15.x suporta `py314` (suporta).
4. Rodar `ruff check --fix .` e `ruff format .` no repo inteiro. Isso reposiciona todos os imports de `finances` (e `tests`) do bloco third-party para o bloco first-party em todo arquivo que os importa (app, testes, e qualquer modulo de `core` que importe `finances`). Exemplo confirmado do agrupamento errado atual: `tests/unit/test_finances/test_app_infra.py:11-15` tem `from finances.apps import FinancesConfig` no bloco third-party junto com `pytest`/`django`, separado por linha em branco de `from core.models import (...)`.
5. Commitar como UM commit mecanico isolado (so reordenacao de imports + config), separado das mudancas de CI, para revisao limpa.

### Parte 2 — Alinhar o CI ao gate canonico

Editar `.github/workflows/ci.yml`. Manter a topologia de 6 jobs (`test`, `code-quality`, `frontend-test`, `frontend-build`, `security`, `build-status`), aplicando:

6. **Postgres do service** (linha 16): `image: postgres:15` → `image: postgres:17` (espelha Supabase prod). Manter env/health-check/ports (linhas 17-27).
7. **Actions** — atualizar TODAS as ocorrencias:
   - `uses: actions/checkout@v3` (linhas 30, 80, 118, 147, 169) → `@v4`.
   - `uses: actions/setup-python@v4` (linhas 33, 83, 171) → `@v5`. Manter `cache: 'pip'`.
   - `actions/setup-node@v4` (linhas 121, 149), `codecov/codecov-action@v3` (linha 70) e `actions/upload-artifact@v4` (linha 194) ja estao OK — nao mexer (v3 do codecov e a major estavel; nao ha gate exigindo bump).
8. **Job `code-quality`** (linhas 75-108):
   - Step "Lint and format with Ruff" (linhas 101-104): trocar
     `ruff check core/ condominios_manager/` → `ruff check .`
     `ruff format --check core/ condominios_manager/` → `ruff format --check .`
     (o `.` cobre `finances/`, `tests/`, `scripts/`; os `per-file-ignores` e `extend-exclude` de `pyproject.toml` ja restringem migrations/frontend/etc.).
   - Step "Type check with mypy" (linhas 106-108): trocar `mypy core/ condominios_manager/` → `mypy core/ condominios_manager/ finances/` (alinha ao escopo de cobertura de `pyproject.toml:379` `source = ["core", "condominios_manager", "finances"]`). NAO adicionar `tests/`/`scripts/` ao mypy — o gate canonico tipa apenas os 3 pacotes de aplicacao.
   - Adicionar NOVO step "Type check with pyright" apos o mypy:
     ```yaml
     - name: Install pyright
       run: pip install pyright
     - name: Type check with pyright
       run: pyright
     ```
     `pyrightconfig.json` ja define `include: [core, condominios_manager, finances, scripts, tests]` (linhas 5-11), `typeCheckingMode: strict` (linha 26) e `pythonVersion: 3.14` (linha 2) — rodar `pyright` sem args usa essa config. `venv`/`venvPath` (`.venv`, linhas 104-106) nao existira no runner CI; setar `pythonPath` via env nao e necessario porque o pip instala global — adicionar nada extra alem de garantir que as deps de runtime ja foram instaladas no step "Install dependencies" (linhas 88-91). Validar que pyright encontra os pacotes; se reclamar de venv ausente, o fallback e o interpretador do sistema (pyright usa o python do PATH quando o venv configurado nao existe).
9. **Job `security`** (linhas 164-199) — tornar gate real:
   - Step bandit (linhas 183-186): `bandit -r core/ condominios_manager/ -ll -f json -o bandit-report.json` → `bandit -r core/ condominios_manager/ finances/ -c pyproject.toml -ll -f json -o bandit-report.json` e REMOVER `continue-on-error: true` (linha 186). `pyproject.toml` ja tem `[tool.bandit]` (linhas 415-427) com `exclude_dirs` (migrations/tests/venv) e `skips = ["B101"]`; passar `-c pyproject.toml` para honrar essa config. Manter saida JSON para o artifact.
   - Step safety (linhas 188-191): `safety check --json` (deprecated) → `safety scan`. REMOVER `continue-on-error: true` (linha 191). Como `safety scan` requer autenticacao/CI token na 3.7.x, usar `safety scan --ci` (modo nao-interativo) e, se autenticacao for inviavel no CI sem segredo, restringir a falha apenas ao bandit e manter `safety scan` informativo com `continue-on-error: true` SOMENTE no safety, documentando no comentario YAML que e por falta de token. Decisao explicita: bandit vira gate hard; safety permanece informativo apenas se o token nao estiver disponivel (preferir transformar em gate se `SAFETY_API_KEY` puder ser adicionado como secret).
   - Step "Upload security reports" (linhas 193-199): manter `if: always()`.
10. **Job `build-status`** (linhas 201-236):
    - `needs:` (linha 204) ja inclui `security` — bom.
    - Adicionar bloco de verificacao do resultado de `security` (espelhando os blocos existentes de `test`/`code-quality`/`frontend-*`, linhas 216-234):
      ```bash
      if [ "${{ needs.security.result }}" != "success" ]; then
        echo "::error::Security audit failed!"
        exit 1
      fi
      ```
      Inserir antes do `echo "Build completed successfully!"` (linha 236). A linha de echo de status de security ja existe (linha 212) — manter.

### Parte 3 — Alvo unico de Python = 3.14

11. `pyproject.toml`:
    - `[project] requires-python = ">=3.12"` (linha 9) → `">=3.14"` (alinha a justificativa da rule sobre PEP 649). Atualizar `classifiers` (linhas 17-19): manter apenas `"Programming Language :: Python :: 3.14"`.
    - `[tool.ruff] target-version` ja vira `py314` na Parte 1 (passo 3).
    - `[tool.mypy] python_version = "3.12"` (linha 285) → `"3.14"`.
12. CI (`.github/workflows/ci.yml`): trocar todas as ocorrencias de `python-version: '3.12'` (linhas 35, 85, 174) e os nomes de step "Set up Python 3.12" (linhas 32, 82, 171) para `3.14`.
13. `render_build.sh` / runtime Render: o repo NAO pina versao de Python para o Render (nao ha `runtime.txt`, `.python-version`, `render.yaml` nem `PYTHON_VERSION` no `render_build.sh`). Criar `.python-version` na raiz com conteudo `3.14` (Render le `.python-version`); alternativamente setar `PYTHON_VERSION=3.14.x` no painel do Render — o plano cria o arquivo versionado por ser reproduzivel. `render_build.sh` (8 comandos: pip install, playwright install chromium, collectstatic, migrate) nao muda.
14. `pyrightconfig.json` ja esta em `3.14` (linha 2) — nao mexer. A nota do comentario sobre `reportShadowedImports` (linhas 84-85) tambem fica.

## Arquivos a criar / modificar

- `pyproject.toml` (modificar): `src` + `known-first-party` (+`finances`,`tests`), `target-version` py314, `requires-python` >=3.14, `classifiers` so 3.14, `[tool.mypy] python_version` 3.14.
- `.github/workflows/ci.yml` (modificar): postgres:17; checkout@v4/setup-python@v5; ruff check/format `.`; mypy `+finances`; novo step pyright; bandit `+finances` -c pyproject.toml sem continue-on-error; safety scan; gate de `security` no build-status; python-version 3.14.
- `.python-version` (criar na raiz): `3.14`.
- Todos os `*.py` que importam `finances`/`tests` (modificados pelo `ruff check --fix .` + `ruff format .` mecanico): reordenacao de imports — sem mudanca de logica. Exemplo confirmado: `tests/unit/test_finances/test_app_infra.py`.
- `tests/unit/test_ci_config_consistency.py` (criar): teste de regressao que prova a consistencia de versao/escopo (ver TDD abaixo).

Sem mudanca de migrations, models, serializers, views, services, frontend ou mobile.

## TDD — cenários de teste

Este plano e majoritariamente config de infra; o gate real e o proprio CI. Ainda assim, adicionar testes Python parametrizados que falham HOJE (red) e travam regressao (`tests/unit/test_ci_config_consistency.py`, lendo os arquivos de config diretamente — fronteira = filesystem, sem mock):

- `test_ci_ruff_lints_whole_repo` — parseia `ci.yml`; asserta que o job code-quality roda `ruff check .` e `ruff format --check .` (nao `core/ condominios_manager/`). (Red hoje: roda so nos 2 pacotes.)
- `test_ci_mypy_includes_finances` — asserta que o step mypy contem `finances` no comando. (Red hoje.)
- `test_ci_runs_pyright` — asserta que existe step de pyright no job code-quality. (Red hoje: ausente.)
- `test_ci_bandit_includes_finances` — asserta que o comando bandit inclui `finances/` e nao tem `continue-on-error` no step. (Red hoje.)
- `test_ci_security_is_a_real_gate` — asserta que `build-status` checa `needs.security.result`. (Red hoje: nao checa.)
- `test_ci_uses_safety_scan_not_check` — asserta `safety scan` e ausencia de `safety check`. (Red hoje.)
- `test_ci_postgres_matches_prod_major` — asserta `image: postgres:17`. (Red hoje: 15.)
- `test_ci_uses_current_actions` — asserta `actions/checkout@v4` e `actions/setup-python@v5`, sem `@v3`/`setup-python@v4`. (Red hoje.)
- `test_python_target_is_consistent` — le `ci.yml` (python-version), `pyproject.toml` (`[tool.mypy].python_version`, `[tool.ruff].target-version`, `requires-python`), `pyrightconfig.json` (`pythonVersion`) e `.python-version`; asserta que TODOS resolvem para a major.minor `3.14`. (Red hoje: 3.12/3.12/py313/3.14/ausente.)
- `test_ruff_finances_is_first_party` — le `pyproject.toml`; asserta `finances` em `[tool.ruff].src` e em `known-first-party`. (Red hoje.)
- `test_python_version_file_exists` — asserta que `.python-version` existe na raiz e e `3.14`. (Red hoje: nao existe.)

Frontend: sem mudanca de contrato FE↔API — nenhum teste vitest/MSW novo.

## Migrations / dados

N/A — nenhuma tabela, coluna ou DDL. Sem RLS, sem backup necessario (CI/config apenas). Nenhuma correcao de dado vivo.

## Constraints (o que NÃO fazer)

- NAO remover Dockerfile/docker-compose/nginx/`scripts/deploy.sh`/`generate_metrics`/`import_caixa_abril` aqui — isso e P0.1. Este plano so referencia.
- NAO adicionar `tests/`/`scripts/` ao `mypy` (o gate canonico tipa so os 3 pacotes de aplicacao: `core`, `condominios_manager`, `finances`); pyright ja cobre tests/scripts via `pyrightconfig.json`.
- NAO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, nem `continue-on-error` para "passar" o CI — se ruff/mypy/pyright/bandit acusarem algo em `finances/` ao entrar no escopo, CORRIGIR o codigo real (escopo do P6.3, dentro do app NOVO `finances/`; nao refatorar o modulo financeiro legado de `core/`).
- NAO tocar no modulo financeiro pessoal legado (`core` Person/Expense/RentPayment, frontend `app/(dashboard)/financial/`) alem do que o reagrupamento de imports mecanico tocar.
- NAO bumpar codecov/setup-node/upload-artifact sem necessidade (ja atuais).
- NAO mudar `pyrightconfig.json` (ja em 3.14) exceto se um erro real de resolucao de venv no CI exigir — nesse caso, ajustar o STEP do CI, nao suprimir regras.
- Se entrar codigo de `finances/` no escopo do ruff/mypy/pyright revelar violacoes em massa que excedam um chore de CI, ESCALAR (abrir achado/plano dedicado) em vez de suprimir — mas a expectativa, dado que o codigo ja roda pre-commit local equivalente, e zero ou poucas correcoes.

## Critérios de aceite (binários)

- [ ] `ruff check .` e `ruff format --check .` passam no repo inteiro (inclui `finances/`, `tests/`, `scripts/`).
- [ ] `finances` aparece em `[tool.ruff].src` e `[tool.ruff.lint.isort].known-first-party`; imports de `finances` agrupados no bloco first-party (verificado em `tests/unit/test_finances/test_app_infra.py`).
- [ ] `mypy core/ condominios_manager/ finances/` passa sem erros nem warnings.
- [ ] `pyright` passa sem erros (config strict incluindo `finances`).
- [ ] `ci.yml`: postgres:17; checkout@v4; setup-python@v5; python-version 3.14 em todos os jobs Python.
- [ ] `ci.yml` job code-quality roda ruff `.`, mypy `+finances` e pyright.
- [ ] `ci.yml` job security: bandit varre `finances/` e e gate hard (sem continue-on-error); `safety scan` no lugar de `safety check`; `build-status` falha se `security` falhar.
- [ ] `[tool.mypy].python_version = "3.14"`, `[tool.ruff].target-version = "py314"`, `requires-python = ">=3.14"`, `pyrightconfig.json` 3.14, `.python-version` = `3.14` — todos consistentes.
- [ ] `tests/unit/test_ci_config_consistency.py` passa (todos verdes; eram red antes).
- [ ] Suite de regressao escopada de `finances/` passa.

## Gate de verificação

Backend (rodar localmente antes de abrir PR):

```bash
ruff check .
ruff format --check .
mypy core/ condominios_manager/ finances/
pyright
python -m pytest tests/unit/test_ci_config_consistency.py -v
python -m pytest tests/unit/test_finances tests/integration/test_finances -p no:xdist -q   # regressao escopada
```

Zero erros E zero warnings em ruff/mypy/pyright/pytest. A suite cheia tem flakiness pre-existente de xdist/Redis — NAO e bloqueio; rodar escopado + a regressao dirigida acima. Frontend nao e afetado (sem mudanca FE), mas confirmar que `frontend-test`/`frontend-build` do CI seguem verdes apos os bumps de action.

Validar o YAML do workflow: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`.

## Handoff

Dois commits sugeridos na branch `chore/ci-and-build-hygiene`:

1. Commit mecanico (Parte 1):
   ```
   chore(ruff): treat finances/tests as first-party and regroup imports

   Add finances and tests to [tool.ruff].src and known-first-party, bump
   ruff target to py314, and run ruff check --fix . / ruff format . so
   finances imports land in the first-party isort block repo-wide.

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```
2. Commit do CI/versao (Partes 2 e 3):
   ```
   chore(ci): align CI to canonical gate and pin Python 3.14

   Run ruff/mypy/pyright/bandit over finances/, make the security job a
   real gate (safety scan, no continue-on-error, checked in build-status),
   bump actions (checkout@v4, setup-python@v5), use postgres:17 to mirror
   prod, and pin Python 3.14 across CI, mypy, ruff target and .python-version.

   Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
   ```

Atualizar a memoria do projeto (`MEMORY.md`) registrando que o CI agora exerce o gate canonico e o alvo Python e 3.14. Se o README documentar gates/versao Python, alinhar (fora do escopo estrito; sinalizar ao plano de docs). O proximo plano pode assumir: (a) `finances/` esta sob ruff/mypy/pyright/bandit no CI; (b) alvo Python unico 3.14; (c) o stack Docker/nginx morto ja foi removido por P0.1 — nao referenciar Dockerfile como ambiente Python a alinhar.
