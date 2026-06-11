# Plano P1.3 — Segurança e correção do pipeline de template de contrato

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P1 · **Branch sugerida:** `fix/contract-template-pipeline` · **Depende de:** P0.1

## Objetivo

O pipeline de template de contrato (editar → salvar → preview → restaurar → gerar PDF) tem falhas de
segurança (SSTI/RCE via Jinja não-sandboxed, path traversal no restore de backup) e bugs de dados que
corrompem ou omitem cláusulas do contrato em produção (cláusula de caução sempre omitida, cláusula de
botijão nunca exibida, template salvo pelo editor WYSIWYG corrompido quando contém `R$100,00`/`R$50,00`).
Este plano fecha as três vulnerabilidades ALTAS, corrige os bugs de renderização/persistência e endurece o
`save_template` para nunca indisponibilizar a geração de PDF por um template inválido — mantendo o módulo
legado de geração intacto e seguindo o padrão de camadas Models→Serializers→Views→Services do projeto.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | SSTI/RCE: `preview_template` compila/executa Jinja arbitrário em `Environment` comum | `core/services/template_management_service.py:219` | Trocar por factory único de `SandboxedEnvironment` |
| ALTO | SSTI/RCE: geração de PDF usa `Environment` comum (FileSystemLoader) | `core/services/contract_service.py:270` | Mesmo factory `SandboxedEnvironment` compartilhado |
| ALTO | Path traversal: `restore_backup` usa `backup_dir / backup_filename` cru de `request.data` | `core/services/template_management_service.py:291` (origem `core/viewsets/template_views.py:236`) | Validar com `resolve()` + `is_relative_to(backup_dir)` + sufixo `.html` |
| ALTO | Cláusula de caução sempre omitida: usa `tenant.deposit_amount` mas o campo é de `Lease` | `core/templates/contract_template.html:436` | Trocar para `lease.deposit_amount` |
| ALTO (FE) | `reconstructFullDocument` usa `String.replace` com replacement string sobre template com `R$100,00`/`R$50,00` → `$1` injeta o body original e corrompe o salvo | `frontend/lib/utils/template-converter.ts:94` | Usar função de replacement (callback) em vez de string |
| MÉDIO | Sem `StrictUndefined`: variável errada renderiza em branco silenciosamente | `template_management_service.py:219` e `contract_service.py:270` | `undefined=StrictUndefined` no factory |
| MÉDIO | `save_template` não valida sintaxe Jinja → save quebrado indisponibiliza TODA geração | `core/services/template_management_service.py:126` | Validar via `env.from_string(content)` antes de gravar; 400 sem sobrescrever |
| MÉDIO | Cláusula botijão: `"Botijão de gás" in furnitures` compara string com lista de objetos `Furniture` → sempre `False` | `core/templates/contract_template.html:502` | Trocar para `furniture_names` (lista de nomes) no contexto |
| MÉDIO | Template/backups em filesystem efêmero no Render, sem rotação | `template_management_service.py:60-72,247` | Avaliar storage durável + rotação (ver "Migrations / dados") |

## Abordagem técnica

Ordem de execução. Cada passo é Red→Green→Refactor→Verify (TDD).

### 1. Factory único de `SandboxedEnvironment` (DRY + corrige SSTI nos dois services)

Hoje há duas construções de `Environment` duplicadas e inseguras:
- `template_management_service.py:219-224` (`Environment(loader=BaseLoader(), autoescape=...)`, filtros `currency`/`extenso`).
- `contract_service.py:270-273` (`Environment(loader=FileSystemLoader(template_path), autoescape=...)`, mesmos filtros).

Criar `core/services/jinja_environment.py` com uma função stateless que centraliza a configuração:

```python
from jinja2 import BaseLoader, FileSystemLoader, StrictUndefined, select_autoescape
from jinja2.sandbox import SandboxedEnvironment
from core.utils import format_currency, number_to_words

def build_contract_jinja_env(loader: BaseLoader | FileSystemLoader) -> SandboxedEnvironment:
    env = SandboxedEnvironment(
        loader=loader,
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
    )
    env.filters["currency"] = format_currency
    env.filters["extenso"] = number_to_words
    return env
```

- `SandboxedEnvironment` bloqueia acesso a atributos/métodos perigosos (`__class__`, `__globals__`, etc.),
  neutralizando a escalada admin→RCE no host via `POST /api/templates/preview/`.
- `StrictUndefined` faz variável inexistente levantar `UndefinedError` em vez de renderizar em branco.
- VERIFICADO: `SandboxedEnvironment` continua expondo `range(...)`, então o loop da tabela de mobílias
  (`contract_template.html:332` `{% for i in range(0, furnitures|length, 2) %}`) segue funcionando.
- Exportar `build_contract_jinja_env` em `core/services/__init__.py` (`from .jinja_environment import build_contract_jinja_env` + adicionar ao `__all__`).

Em `contract_service.py:render_contract_template` (linhas 269-277): substituir a construção local por
`env = build_contract_jinja_env(FileSystemLoader(template_path))` e remover os imports agora não usados
(`Environment`, `select_autoescape` permanece só se usado; `format_currency`/`number_to_words` saem do
import direto se não mais referenciados — verificar com ruff F401).

Em `template_management_service.py:preview_template` (linhas 219-224): substituir por
`env = build_contract_jinja_env(BaseLoader())`. Remover imports não usados.

### 2. Contexto: adicionar `furniture_names` e remover a dependência de objetos na cláusula botijão

Em `contract_service.py:prepare_contract_context` (dict de contexto linhas 202-220), adicionar:

```python
"furniture_names": [f.name for f in lease_furnitures],
```

Mantém `"furnitures": lease_furnitures` (a tabela de mobílias em `contract_template.html:334/336` usa
`{{ furnitures[i] }}` que depende de `Furniture.__str__` → `self.name`, e continua válido). `furniture_names`
é a lista de strings usada pela condicional de botijão. Atualizar o docstring/contexto na linha 158
("Dictionary containing all template variables including landlord") se necessário — sem inventar campos.

### 3. Corrigir `contract_template.html` (bugs de dados que rodam em prod)

- Linha 436: `{% if tenant.deposit_amount and tenant.deposit_amount > 0 %}` → `{% if lease.deposit_amount and lease.deposit_amount > 0 %}`.
- Linhas 439 e 440: `{{ tenant.deposit_amount | currency }}` / `{{ tenant.deposit_amount | extenso }}` → `lease.deposit_amount`. (`deposit_amount` é `DecimalField(null=True)` em `Lease`, confirmado em `core/models.py:676`; em `Tenant` não existe.)
- Linha 502: `{% if "Botijão de gás" in furnitures %}` → `{% if "Botijão de gás" in furniture_names %}`.
  (A grafia exata depende do `name` cadastrado no banco — manter a string idêntica à atual; a correção é
  apenas trocar a variável de objetos para nomes.)

Como `StrictUndefined` agora está ativo, qualquer variável remanescente que não exista no contexto fará a
geração falhar — por isso o passo 6 (sincronizar a lista documentada com o contexto real) é obrigatório
antes de fechar.

### 4. Validar `backup_filename` em `restore_backup` (corrige path traversal)

Em `template_management_service.py:restore_backup` (linhas 290-295), antes de qualquer cópia:

```python
backup_dir = cls.get_backup_directory().resolve()
candidate = (backup_dir / backup_filename).resolve()
if candidate.suffix != ".html" or not candidate.is_relative_to(backup_dir):
    msg = "Nome de backup inválido"
    raise ValueError(msg)
backup_path = candidate
if not backup_path.exists():
    msg = f"Backup file not found: {backup_filename}"
    raise FileNotFoundError(msg)
```

- `resolve()` + `is_relative_to(backup_dir)` rejeita `../../.env`, paths absolutos e symlinks que escapem do
  diretório de backups; o sufixo `.html` impede sobrescrever `contract_template.html` por um arquivo arbitrário.
- `ValueError` já é tratado pela view? NÃO — `restore_backup` na view (`template_views.py:244-270`) captura
  `FileNotFoundError`/`PermissionError`/`OSError`/`Exception`, mas não `ValueError`. Adicionar um `except ValueError`
  retornando `status.HTTP_400_BAD_REQUEST` com `{"error": str(e)}` (padrão idêntico ao `save_template` da view,
  linhas 108-109). Sem isso, o `ValueError` cairia no `except Exception` genérico → 500 (aceitável mas impreciso;
  o gate pede 400).

### 5. Validar sintaxe Jinja em `save_template` (não indisponibilizar geração)

Em `template_management_service.py:save_template` (após o guard de conteúdo vazio, linhas 146-148, e ANTES de
criar backup/gravar nas linhas 158-164):

```python
from jinja2 import BaseLoader  # já importado no módulo
from jinja2.exceptions import TemplateSyntaxError
...
env = build_contract_jinja_env(BaseLoader())
try:
    env.from_string(content)
except TemplateSyntaxError as exc:
    msg = f"Template inválido: erro de sintaxe Jinja na linha {exc.lineno}: {exc.message}"
    raise ValueError(msg) from exc
```

- `from_string` compila sem renderizar (não precisa de contexto/lease) — só valida sintaxe.
- A view `save_template` (`template_views.py:108-109`) já mapeia `ValueError` → 400, então um template inválido
  retorna 400 SEM tocar o arquivo em disco nem criar backup. O template anterior (válido) permanece e a geração
  de PDF continua disponível.
- Mensagem de erro em PT (usuário) com `lineno` para localizar o erro no editor.

### 6. Sincronizar a lista de variáveis documentada (frontend) com `prepare_contract_context`

`frontend/app/(dashboard)/contract-template/page.tsx` já documenta corretamente `{{ lease.deposit_amount ... }}`
(linhas 389-390) e `{{ furniture.name }}` (linha 383). Ajustes:
- Adicionar à seção "Loops/Condicionais" ou "Variáveis de Locação" a menção a `furniture_names` (lista de nomes
  para condicionais tipo botijão), distinguindo de `furnitures` (lista de objetos `Furniture` para o loop da tabela).
- Auditar cada `{{ ... }}` listado na página contra as chaves reais do dict de contexto em
  `prepare_contract_context` (linhas 202-220: `landlord, tenant, building_number, apartment_number, furnitures,
  furniture_names, validity, start_date, final_date, rental_value, next_month_date, tag_fee, cleaning_fee,
  valor_total, rules, lease, valor_tags, tag_unit_price`). Remover/ajustar qualquer variável documentada que não
  exista (com `StrictUndefined` ativo, documentar uma variável inexistente induz o usuário a quebrar a geração).
  NOTA: `building_address` (linha 357) NÃO está no contexto — confirmar e remover da doc OU adicionar ao contexto
  (`lease.apartment.building.address`); decidir por remover da doc (YAGNI) salvo se já for usado no template atual
  (`grep building_address core/templates/contract_template.html`).

### 7. Corrigir `reconstructFullDocument` (corrupção do template salvo — frontend)

`frontend/lib/utils/template-converter.ts:94`:

```ts
return originalDocument.replace(BODY_CONTENT_REGEX, `<body>\n${bodyContent}\n  </body>`);
```

`String.prototype.replace` com replacement string interpreta `$1`, `$&`, `$$` etc. Como o body contém literais
como `R$100,00` e `R$50,00` (ver `contract_template.html:489` "multa de R$100,00"), qualquer `$1`..`$9`/`$&`
presente no `bodyContent` injeta trechos do match original e corrompe o documento salvo. Corrigir usando a forma
de callback (que NÃO interpreta os padrões `$`):

```ts
return originalDocument.replace(
  BODY_CONTENT_REGEX,
  () => `<body>\n${bodyContent}\n  </body>`,
);
```

A função de replacement recebe os grupos como args mas retorna a string literal sem nenhuma substituição de `$`.
(Alternativa equivalente: escapar `bodyContent.replace(/\$/g, '$$$$')` — preferir o callback por ser KISS e não
mutar o conteúdo.)

### 8. Storage durável de template/backups (MÉDIO — avaliar e decidir no plano, implementar só se P0.1 não cobrir)

O template e os backups vivem em `core/templates/` e `core/templates/backups/` no filesystem do Render, que é
efêmero — um deploy/restart perde edições e backups. Decisão a tomar nesta tarefa:
- Se P0.1 (dependência) já moveu a geração/persistência para storage durável, este plano apenas confirma que
  template e backups herdam esse storage e adiciona rotação.
- Caso contrário, escopo aqui: persistir o template ativo e os backups num modelo (ex.: `ContractTemplate` /
  `ContractTemplateBackup` com `AuditMixin` + `SoftDeleteMixin`) OU em object storage. Esta é uma mudança maior;
  se exceder o escopo da branch, registrar como follow-up explícito (plano P-seguinte) e NÃO deixar meio-feito.
- Rotação: manter no máximo N backups por timestamp (ex.: 20) + sempre preservar `contract_template_DEFAULT.html`,
  apagando os mais antigos em `save_template`/`restore_backup`. Implementar como método stateless no service.

Constraint: não introduzir persistência parcial. Ou entrega o storage durável completo (model+migration+RLS+
service+testes) nesta branch, ou difere para um plano próprio com nota de handoff. A rotação em filesystem pode
ser entregue independentemente do storage durável e é de baixo risco.

## Arquivos a criar / modificar

- **Criar** `core/services/jinja_environment.py` — `build_contract_jinja_env(loader)` (SandboxedEnvironment + StrictUndefined + filtros).
- **Modificar** `core/services/__init__.py` — exportar `build_contract_jinja_env` (import + `__all__`).
- **Modificar** `core/services/contract_service.py` — `render_contract_template` usa o factory; `prepare_contract_context` adiciona `furniture_names`; limpar imports não usados (`Environment`, etc.).
- **Modificar** `core/services/template_management_service.py` — `preview_template` usa o factory; `save_template` valida sintaxe; `restore_backup` valida `backup_filename` (resolve+is_relative_to+.html); aplicar rotação se incluída.
- **Modificar** `core/viewsets/template_views.py` — `restore_backup` view captura `ValueError` → 400.
- **Modificar** `core/templates/contract_template.html` — `lease.deposit_amount` (linhas 436/439/440); `furniture_names` na condicional botijão (linha 502).
- **Modificar** `frontend/lib/utils/template-converter.ts` — `reconstructFullDocument` usa replacement callback.
- **Modificar** `frontend/app/(dashboard)/contract-template/page.tsx` — documentar `furniture_names`; sincronizar lista de variáveis com o contexto; remover `building_address` se não estiver no contexto/template.
- **Modificar/criar testes** `tests/unit/test_jinja_environment.py` (novo), `tests/unit/test_template_service.py`, `tests/unit/test_contract_service.py`, `tests/integration/test_template_views.py`.
- **Modificar testes FE** `frontend/lib/utils/__tests__/template-converter.test.ts` (criar se não existir).
- (Condicional ao passo 8) **Criar** migration de model de template/backup + RLS, se o storage durável for entregue nesta branch.

## TDD — cenários de teste

### Backend — `build_contract_jinja_env` (`tests/unit/test_jinja_environment.py`)
- `test_env_is_sandboxed` — instância é `SandboxedEnvironment`.
- `test_blocks_dunder_access` — `{{ ''.__class__.__mro__ }}` levanta `SecurityError` ao renderizar (prova anti-RCE).
- `test_strict_undefined_raises` — `{{ inexistente }}` levanta `UndefinedError`.
- `test_currency_and_extenso_filters_registered` — render de `{{ 1500 | currency }}` e `{{ 1500 | extenso }}` produz saída esperada.
- `test_range_available_for_furniture_loop` — `{% for i in range(0,4,2) %}{{ i }}{% endfor %}` renderiza `02` (regressão da tabela de mobílias).

### Backend — `preview_template` / SSTI (`tests/unit/test_template_service.py`)
- `test_preview_rejects_ssti_payload` — `preview_template("{{ ''.__class__.__mro__[1].__subclasses__() }}", lease_id)` levanta erro de segurança (não executa) — **regressão do achado ALTO**.
- `test_preview_renders_valid_template` — template válido com `{{ tenant.name }}` renderiza o nome (caminho feliz).
- `test_preview_strict_undefined_raises_on_unknown_var` — `{{ variavel_que_nao_existe }}` levanta erro em vez de string vazia.

### Backend — `save_template` (`tests/unit/test_template_service.py`)
- `test_save_rejects_invalid_jinja_without_overwriting` — conteúdo `"{% if %}"` levanta `ValueError` E o arquivo em disco permanece o anterior (ler o arquivo e comparar) — **regressão do achado MÉDIO (save quebrado indisponibiliza geração)**.
- `test_save_invalid_jinja_creates_no_backup` — nenhum novo backup é criado quando a sintaxe é inválida.
- `test_save_valid_template_persists_and_backs_up` — caminho feliz mantém comportamento atual (backup + gravação).

### Backend — `restore_backup` / path traversal (`tests/unit/test_template_service.py`)
- `test_restore_rejects_path_traversal` — `restore_backup("../../.env")` levanta `ValueError` e NÃO sobrescreve `contract_template.html` — **regressão do achado ALTO**.
- `test_restore_rejects_absolute_path` — `restore_backup(str(tmp_path / 'evil.html'))` (fora do backup_dir) levanta `ValueError`.
- `test_restore_rejects_non_html_suffix` — `restore_backup("contract_template_backup_x.txt")` levanta `ValueError`.
- `test_restore_valid_backup_succeeds` — caminho feliz: restaura um backup legítimo dentro do diretório.

### Backend — geração de contrato / template fixes (`tests/unit/test_contract_service.py`)
- `test_context_includes_furniture_names` — `prepare_contract_context` retorna `furniture_names` como lista de strings dos nomes dos móveis do lease.
- `test_deposit_clause_rendered_when_lease_has_deposit` — render do template com `lease.deposit_amount > 0` inclui o texto da cláusula de caução — **regressão do achado ALTO (cláusula sempre omitida)**.
- `test_deposit_clause_omitted_when_no_deposit` — `lease.deposit_amount = None` omite a cláusula (sem erro com StrictUndefined).
- `test_botijao_clause_rendered_when_furniture_present` — móvel com `name="Botijão de gás"` faz a cláusula de botijão aparecer — **regressão do achado MÉDIO (`in furnitures` sempre False)**.
- `test_botijao_clause_omitted_when_absent` — sem o móvel, a cláusula não aparece.
- `test_render_contract_template_uses_sandboxed_env` — render integrado não permite payload SSTI no template em disco (defesa em profundidade).

### Backend — view (`tests/integration/test_template_views.py`)
- `test_restore_invalid_filename_returns_400` — `POST /api/templates/restore/` com `backup_filename="../../.env"` retorna 400 (não 500/não sobrescreve).
- `test_save_invalid_template_returns_400` — `POST /api/templates/save/` com Jinja inválido retorna 400 e mantém o template atual.
- `test_preview_ssti_payload_returns_safe` — `POST /api/templates/preview/` com payload SSTI não executa código (erro tratado, sem vazamento).

### Frontend — `reconstructFullDocument` (`frontend/lib/utils/__tests__/template-converter.test.ts`, Vitest)
- `reconstructFullDocument preserva R$100,00 e R$50,00 no body` — body contendo `multa de R$100,00 ... R$50,00` é reinjetado idêntico (sem corromper via `$1`) — **regressão do achado ALTO FE**.
- `reconstructFullDocument preserva sequência $& e $$ literais` — edge case dos padrões especiais de replacement.
- `reconstructFullDocument retorna bodyContent quando não é documento completo` — comportamento atual preservado.
- `roundtrip jinjaToWysiwyg → wysiwygToJinja → reconstructFullDocument` mantém `{{ lease.deposit_amount | currency }}` intacto.

## Migrations / dados

- **Sem migration** se o passo 8 ficar restrito a rotação em filesystem (decisão recomendada para esta branch) — então **N/A** para migrations.
- **Se** o storage durável de template/backups (passo 8) for entregue aqui: criar model(s) com `AuditMixin` +
  `SoftDeleteMixin`, gerar migration via `makemigrations`, e **habilitar RLS na mesma migration** seguindo o
  padrão `core/migrations/0047_enable_row_level_security.py`
  (`migrations.RunSQL("ALTER TABLE public.<tabela> ENABLE ROW LEVEL SECURITY;", reverse_sql="ALTER TABLE public.<tabela> DISABLE ROW LEVEL SECURITY;")`,
  SQL estático, sem f-string). **Backup antes de qualquer migrate** (`python scripts/backup_db.py`). Rodar o
  Supabase security advisor após DDL em prod.
- **Correção de dado vivo:** os bugs de caução/botijão são de template (código), não de dados — nenhuma linha de
  banco a corrigir. Em prod, o `contract_template.html` ativo pode ter divergido via editor; após o deploy, validar
  que a versão em disco/storage contém `lease.deposit_amount` e `furniture_names` (se o usuário tiver salvo uma
  versão custom, orientar restaurar do DEFAULT ou reaplicar as correções no editor).

## Constraints (o que NÃO fazer)

- NÃO refatorar o módulo financeiro legado nem qualquer área fora do pipeline de template/contrato.
- NÃO alterar o loop da tabela de mobílias (`furnitures[i]` / `range`) — apenas adicionar `furniture_names`;
  `furnitures` (objetos) permanece para a tabela.
- NÃO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, nem `from __future__ import annotations`.
- NÃO usar `FORCE ROW LEVEL SECURITY` (quebraria o backend que faz bypass como `postgres`).
- NÃO adicionar policies permissivas para "resolver" o aviso `rls_enabled_no_policy` (é o estado correto).
- NÃO mockar internals nos testes — apenas fronteiras externas (filesystem via `tmp_path`/`monkeypatch BASE_DIR`,
  Chrome/PDF via `mock_pdf_generation`, HTTP no FE via MSW). Renderizar Jinja de verdade (é o que se testa).
- NÃO criar re-exports nem shims de compatibilidade; atualizar todos os consumidores dos `Environment` removidos.
- NÃO entregar o storage durável (passo 8) pela metade — completo nesta branch OU diferido para plano próprio.
- NÃO relaxar o `SandboxedEnvironment` adicionando globals/atributos perigosos para "fazer um template funcionar".

## Critérios de aceite (binários)

- [ ] `core/services/jinja_environment.py` existe e é a ÚNICA construção de Environment usada por `contract_service` e `template_management_service`.
- [ ] `preview_template` e `render_contract_template` usam `SandboxedEnvironment` com `StrictUndefined`.
- [ ] Payload SSTI em `POST /api/templates/preview/` não executa código (teste prova).
- [ ] `restore_backup("../../.env")` é rejeitado (ValueError → 400) e não sobrescreve `contract_template.html`.
- [ ] `save_template` com Jinja inválido retorna 400 e NÃO altera o arquivo/cria backup.
- [ ] Cláusula de caução aparece quando `lease.deposit_amount > 0` e some quando `None` (sem erro StrictUndefined).
- [ ] Cláusula de botijão aparece quando há móvel `Botijão de gás` (via `furniture_names`).
- [ ] `prepare_contract_context` inclui `furniture_names` (lista de strings).
- [ ] `reconstructFullDocument` preserva `R$100,00`/`R$50,00` e padrões `$&`/`$1` literais no body.
- [ ] Lista de variáveis em `contract-template/page.tsx` reflete exatamente as chaves de `prepare_contract_context` (sem `building_address` órfão).
- [ ] Rotação de backups implementada (filesystem) OU storage durável completo OU follow-up documentado no Handoff.
- [ ] Todo bug corrigido tem teste de regressão correspondente.

## Gate de verificação

Backend (escopado nos arquivos editados + regressão dirigida):

```bash
ruff check core/services/jinja_environment.py core/services/contract_service.py core/services/template_management_service.py core/viewsets/template_views.py
ruff format --check core/services/jinja_environment.py core/services/contract_service.py core/services/template_management_service.py core/viewsets/template_views.py
mypy core/
pyright
python -m pytest tests/unit/test_jinja_environment.py tests/unit/test_template_service.py tests/unit/test_contract_service.py tests/integration/test_template_views.py
```

Frontend:

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Zero erros E zero warnings em Ruff, mypy, Pyright, ESLint, TypeScript e pytest. A suíte cheia tem flakiness
pré-existente de xdist/Redis — rodar escopado + regressão dirigida; flakiness pré-existente não é bloqueio.

## Handoff

Commit sugerido:

```
fix(contract): sandbox Jinja, block backup path traversal, fix deposit/botijão clauses

- Add core/services/jinja_environment.build_contract_jinja_env (SandboxedEnvironment + StrictUndefined),
  shared by ContractService.render_contract_template and TemplateManagementService.preview_template (fixes SSTI/RCE)
- Validate backup_filename in restore_backup (resolve + is_relative_to + .html); view returns 400 (fixes path traversal)
- Validate Jinja syntax in save_template before persisting (invalid template -> 400, no overwrite)
- Template: use lease.deposit_amount (deposit clause was always omitted) and furniture_names (botijão clause never matched)
- prepare_contract_context: add furniture_names
- Frontend: reconstructFullDocument uses replacement callback (R$100,00/R$50,00 no longer corrupt saved template)
- Sync documented template variables with prepare_contract_context

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar o estado: marcar este plano como CONCLUÍDO no índice de planos e registrar em
`C:/Users/alvar/.claude/projects/.../memory/` (entrada `project_contract_pdf_prod_failure.md`) que o pipeline
de template foi endurecido (sandbox + traversal + save-validation + clauses).

O próximo plano assume: (a) a geração de PDF já usa template sandboxed e StrictUndefined, então qualquer
variável nova de contexto precisa existir no dict de `prepare_contract_context`; (b) se o storage durável de
template/backups NÃO foi entregue aqui, ele permanece como follow-up explícito (filesystem efêmero no Render
ainda perde edições entre deploys) — priorizar num plano subsequente.
