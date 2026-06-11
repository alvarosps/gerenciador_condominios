# Plano HF-1 — 500 no PATCH /api/tenants (edição de dia de vencimento) + dados legados inválidos

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** HOTFIX (bloqueia operação em produção) · **Branch sugerida:** `fix/tenant-update-500-validation` (a partir de `master`) · **Depende de:** nenhum (independente do roadmap P0–P8; pode rodar antes/em paralelo a tudo)
>
> **For agentic workers:** REQUIRED SUB-SKILL: usar `superpowers:subagent-driven-development` ou `superpowers:executing-plans` + `/prompt-session` (TDD + audit). Passos usam checkbox (`- [ ]`).

**Goal:** Editar o dia de vencimento (e qualquer campo) de qualquer inquilino via UI sem 500 — convertendo `ValidationError` do Django em 400 DRF (mata a classe do bug em tenants/leases/apartments/finances) e saneando os dados legados inválidos em produção.

**Architecture:** Handler global de exceção DRF (`core/exceptions.py`, semente do que o P4.1 vai estender) + data migration de normalização de `marital_status` + runbook de correção manual dos registros ambíguos + melhoria pontual no `getErrorMessage` do frontend para exibir erros por campo.

**Tech Stack:** Django 5.2 / DRF 3.15, pytest, Next.js 14 + Vitest.

---

## Causa raiz (debug 2026-06-11, verificado adversarialmente)

Fluxo do bug — reproduzido localmente contra o espelho do prod e confirmado com dados vivos do Supabase:

1. `LeaseFormModal.onSubmit` dispara `PATCH /api/tenants/7/ {"due_day":10}` quando o dia de vencimento muda (`frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx:325-327`). Esse PATCH roda **antes** do update do lease; quando falha, o `catch` aborta o submit inteiro — por isso "nada salva". Alterar só `prepaid_until` funciona porque vai no payload do Lease, não dispara o PATCH do tenant.
2. O payload passa no `is_valid()` (PATCH parcial valida só `due_day`), mas `TenantSerializer.update()` chama `instance.full_clean()` (`core/serializers.py:345`), que revalida **todos** os campos armazenados da linha.
3. O tenant 7 tem `marital_status='Solteira'` (forma feminina) gravado no banco — valor que **nunca** esteve em `Tenant.MARITAL_STATUS_CHOICES` (`core/models.py:479-491`; os valores legados são só masculinos). `full_clean()` levanta `django.core.exceptions.ValidationError({'marital_status': ["Value 'Solteira' is not a valid choice."]})`.
4. Não há `EXCEPTION_HANDLER` customizado em `REST_FRAMEWORK` (settings). O handler default do DRF 3.15 só converte `APIException`/`Http404`/`PermissionDenied` — `ValidationError` do Django re-levanta → **HTTP 500**.
5. Mesmo que o serializer não chamasse `full_clean`, `Tenant.save()` chama de novo (`core/models.py:545-548`) — o fix tem que ser na conversão da exceção, não em remover um call site.

**Blast radius verificado em prod (consultas de 2026-06-11, pós-incidente):**

| Tenants | Campo inválido armazenado | Comportamento hoje |
| --- | --- | --- |
| 2, 4, 7 | `marital_status='Solteira'` | **500** em qualquer PATCH/PUT |
| 35 | `marital_status='-'` **e** `phone='-'` | **500** |
| 40 | `due_day=860` | **500** |
| 44, 45, 46 | `phone` com 9 dígitos (sem DDD) | **500** |
| 11, 24, 27, 32 | CPF com dígito verificador errado | **400** (o `TenantSerializer.validate` re-checa CPF no `is_valid` e o DRF converte) — bloqueado mesmo assim |

Mesma classe de bug exposta em: `PUT/PATCH /api/leases/{id}/` (`core/serializers.py:539` + `core/models.py:750`; inclui a *time bomb* `validate_lease_dates` — lease com `start_date` >10 anos no passado fica permanentemente in-editável), `PUT/PATCH /api/apartments/{id}/` (`core/serializers.py:221`) e `finances` `BillViewSet._transition` (`finances/viewsets/crud_views.py:400-403`, único action sem wrap). Building/Furniture/Dependent e o restante do `finances` NÃO são expostos.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| CRITICO | `ValidationError` do Django escapa como 500 em update parcial (tenants/leases/apartments + `BillViewSet._transition`) | `core/serializers.py:345,539,221`; `core/models.py:548,750`; settings sem `EXCEPTION_HANDLER` | `core/exceptions.py` com handler global convertendo DjangoValidationError → DRF 400 |
| CRITICO | 8 tenants ativos em prod com dado armazenado inválido (3 `Solteira`, 1 `-`, 1 `due_day=860`, 3 fones sem DDD) bloqueiam qualquer edição | `core_tenant` (prod) ids 2,4,7,35,40,44,45,46 | data migration normaliza `marital_status`; runbook via UI para os ambíguos |
| MEDIO | Choices legadas masculinas de `marital_status` mortas após normalização | `core/models.py:479-491` | normalizar masculinas → forma `(a)` e remover entradas legadas das choices |
| BAIXO | `getErrorMessage` não exibe erros por campo do DRF (`{"campo": [...]}` cai no genérico "Dados inválidos") | `frontend/lib/utils/error-handler.ts:83-143` | exibir o primeiro erro de campo (`campo: mensagem`) |

## Decisões de design

- **Conversão global no handler, não try/except por serializer**: DRY — um ponto mata a classe inteira nos 3 endpoints core + finances. É o mecanismo canônico do DRF. O `core/exceptions.py` criado aqui é exatamente o arquivo que o **P4.1** planeja estender (unificação do shape `{"error"}`→`{"detail"}`) — sem conflito, só semente.
- **Manter `full_clean()` estrito** (não usar `exclude` de campos não alterados): a validação total é proteção de qualidade de dado intencional. Com o handler (erro 400 claro apontando o campo) + dados saneados, o custo desaparece. Afrouxar mascararia dado ruim.
- **Normalizar dado, não afrouxar choices**: NÃO adicionar `'Solteira'` às choices — isso perpetuaria o legado. A migration converte para a forma canônica `(a)`.
- **Não mexer no fluxo do `LeaseFormModal`** (usar a action `change_due_date` do lease em vez de PATCH cru no tenant é refactor do P4.x; fora de escopo do hotfix).
- **Não normalizar CPF/CNPJ aqui** — formatação/normalização e unicidade são escopo do **P2.4** (`docs/plans/2026-06-11-p2-4-core-data-integrity-migrations-plan.md`). Os 4 CPFs com dígito verificador **errado** (11, 24, 27, 32) não são automatizáveis — precisam do documento real (runbook).

## Mitigação imediata (opcional, antes do deploy)

Desbloqueia o caso reportado (tenant 7 / Apto 112) em segundos, via Supabase MCP/SQL Editor — idempotente com a migration que vem depois:

```sql
UPDATE core_tenant SET marital_status = 'Solteiro(a)' WHERE marital_status = 'Solteira';  -- 3 linhas: ids 2, 4, 7
```

---

## Tarefas

### Task 1: `core/exceptions.py` — handler global DjangoValidationError → 400

**Files:**
- Create: `core/exceptions.py`
- Create: `tests/unit/test_exceptions.py`
- Modify: `condominios_manager/settings.py` (bloco `REST_FRAMEWORK`)

- [ ] **Step 1: Escrever os testes unitários (devem falhar)**

`tests/unit/test_exceptions.py`:

```python
"""Tests for the global DRF exception handler (core/exceptions.py)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status

from core.exceptions import custom_exception_handler


class TestCustomExceptionHandler:
    def test_django_validation_error_with_message_dict_returns_400_field_shape(self) -> None:
        exc = DjangoValidationError({"marital_status": ["Value 'Solteira' is not a valid choice."]})
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "marital_status" in response.data

    def test_django_validation_error_plain_message_returns_400_non_field_errors(self) -> None:
        exc = DjangoValidationError("CPF inválido")
        response = custom_exception_handler(exc, {})
        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "non_field_errors" in response.data

    def test_http404_still_maps_to_404(self) -> None:
        response = custom_exception_handler(Http404(), {})
        assert response is not None
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unknown_exception_returns_none(self) -> None:
        assert custom_exception_handler(RuntimeError("boom"), {}) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/unit/test_exceptions.py -v` → FAIL (`ModuleNotFoundError: core.exceptions`)

- [ ] **Step 3: Implementar `core/exceptions.py`**

```python
"""Global DRF exception handling.

Converts django.core.exceptions.ValidationError (raised e.g. by full_clean()
inside serializer.update()/model.save()) into a DRF 400 instead of a 500.
Seed for P4.1 (error-shape unification).
"""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DjangoValidationError):
        detail: Any = (
            exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
        )
        exc = ValidationError(detail)
    return exception_handler(exc, context)
```

(Nota: `hasattr(exc, "message_dict")` é o padrão já usado em `core/views.py:564-566` — a property levanta quando o erro não é dict-based, e `hasattr` retorna False nesse caso.)

- [ ] **Step 4: Registrar no settings**

Em `condominios_manager/settings.py`, dentro do dict `REST_FRAMEWORK` existente (linha ~217):

```python
"EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
```

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/unit/test_exceptions.py -v` → PASS

- [ ] **Step 6: Commit**

```bash
git add core/exceptions.py tests/unit/test_exceptions.py condominios_manager/settings.py
git commit -m "fix(api): convert django ValidationError to DRF 400 via global exception handler"
```

### Task 2: Teste de integração — repro exato do bug de prod

**Files:**
- Create: `tests/integration/test_exception_handler.py` (arquivo que o P4.1 também planeja — criar aqui, P4.1 estende)

- [ ] **Step 1: Escrever os testes (devem falhar SEM a Task 1; com ela, passar)**

Cenários obrigatórios (usar o padrão de auth/fixtures de `tests/integration/test_tenant_crud.py`; semear dado inválido com `Tenant.all_objects.filter(pk=...).update(...)` — `queryset.update()` bypassa `save()`/`full_clean()`, e não há CHECK constraint no banco para esses campos, verificado em prod):

```python
class TestStoredInvalidDataPartialUpdate:
    def test_patch_due_day_with_stored_invalid_marital_status_returns_400(self, ...):
        """Repro do incidente de prod (tenant 7): PATCH {'due_day': 10} numa linha
        com marital_status='Solteira' deve dar 400 apontando marital_status — não 500."""
        # seed: tenant válido; depois Tenant.all_objects.filter(pk=t.pk).update(marital_status="Solteira")
        # PATCH /api/tenants/{id}/ {"due_day": 10} como admin
        # assert 400; assert "marital_status" in response.json()

    def test_patch_due_day_with_stored_invalid_phone_returns_400(self, ...):
        """Linha com phone de 9 dígitos (sem DDD) — classe dos tenants 44/45/46."""

    def test_patch_on_valid_tenant_still_returns_200(self, ...):
        """Regressão: PATCH {'due_day': 15} em linha válida continua 200 e persiste."""

    def test_patch_lease_with_stored_invalid_validity_months_returns_400(self, ...):
        """Mesma classe no Lease: update(validity_months=120) + PATCH {'tag_fee': '20.00'} → 400, não 500."""
```

- [ ] **Step 2: Rodar**

Run: `python -m pytest tests/integration/test_exception_handler.py -v` → PASS (com Task 1 no lugar). Para provar que o teste é real: `git stash` do settings (handler fora) → os testes de 400 devem FALHAR com 500 → `git stash pop`.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_exception_handler.py
git commit -m "test(api): integration repro — stored-invalid rows 400 (not 500) on partial update"
```

### Task 3: Data migration — normalizar `marital_status` + remover choices legadas mortas

**Files:**
- Modify: `core/models.py:479-491` (`MARITAL_STATUS_CHOICES`)
- Create: `core/migrations/<próxima livre via makemigrations>` (NÃO fixar número; P2.4 também vai consumir a sequência)
- Create: `tests/unit/test_migrations_marital_status.py`

- [ ] **Step 1: Verificar consumidores das choices legadas**

Run: `git grep -nE "Solteiro\"|Casado\"|Divorciado\"|Viúvo\"|Separado" frontend/ mobile/ core/ scripts/`
Esperado: frontend/mobile enviam apenas as formas canônicas `(a)` / `União Estável`. Se o mobile enviar valor legado, MANTER essa choice e registrar no handoff (P3.1 é dono do mobile).

- [ ] **Step 2: Verificar se existe linha com `Separado` em prod**

Via Supabase MCP (read-only): `SELECT marital_status, count(*) FROM core_tenant GROUP BY 1 ORDER BY 2 DESC;`
Se `count('Separado') == 0` e nenhum consumidor envia → remover também a choice `Separado`; senão, manter.

- [ ] **Step 3: Atualizar `MARITAL_STATUS_CHOICES`** (mantendo o resultado dos Steps 1–2):

```python
MARITAL_STATUS_CHOICES = [
    ("Solteiro(a)", "Solteiro(a)"),
    ("Casado(a)", "Casado(a)"),
    ("Divorciado(a)", "Divorciado(a)"),
    ("Viúvo(a)", "Viúvo(a)"),
    ("União Estável", "União Estável"),
    # ("Separado", "Separado"),  # manter SOMENTE se Step 2 encontrar linhas/consumidores
]
```

- [ ] **Step 4: Gerar a migration e adicionar o RunPython de normalização**

Run: `python manage.py makemigrations core` (gera o `AlterField` das choices — no-op de SQL). Editar a migration NOVA adicionando ANTES do `AlterField`:

```python
MARITAL_STATUS_NORMALIZATION = {
    # feminino → canônico (dados nunca-válidos; causa do incidente)
    "Solteira": "Solteiro(a)",
    "Casada": "Casado(a)",
    "Divorciada": "Divorciado(a)",
    "Viúva": "Viúvo(a)",
    # legado masculino → canônico (válidos hoje, mortos após esta migration)
    "Solteiro": "Solteiro(a)",
    "Casado": "Casado(a)",
    "Divorciado": "Divorciado(a)",
    "Viúvo": "Viúvo(a)",
}


def normalize_marital_status(apps, schema_editor):
    tenant_model = apps.get_model("core", "Tenant")
    for legacy, canonical in MARITAL_STATUS_NORMALIZATION.items():
        tenant_model.objects.filter(marital_status=legacy).update(marital_status=canonical)
```

`migrations.RunPython(normalize_marital_status, migrations.RunPython.noop)`.
Atenção: confirmar que o historical model usa manager plain (sem filtro de soft-delete): `git grep -n use_in_migrations core/models.py` — se `SoftDeleteManager` tiver `use_in_migrations=True`, trocar para `tenant_model._base_manager` no RunPython para alcançar linhas soft-deletadas.

- [ ] **Step 5: Teste do mapeamento**

`tests/unit/test_migrations_marital_status.py` — importar `MARITAL_STATUS_NORMALIZATION` do módulo da migration (mesmo padrão planejado no P2.4 para `test_migrations_cpf_normalization.py`):

```python
def test_all_feminine_and_legacy_masculine_forms_map_to_canonical_choices():
    """Todo valor do mapa aponta para uma choice canônica vigente."""

def test_placeholder_dash_is_not_in_the_map():
    """'-' é ambíguo (runbook manual) — a migration NÃO pode inventar valor."""
```

- [ ] **Step 6: Backup local + migrar local + verificar**

```bash
python scripts/backup_db.py
python manage.py migrate core
```
Verificar (shell read-only): `Tenant.objects.filter(marital_status="Solteira").count() == 0` e `Tenant.objects.get(pk=7).full_clean()` não levanta mais.

- [ ] **Step 7: Commit**

```bash
git add core/models.py core/migrations/ tests/unit/test_migrations_marital_status.py
git commit -m "fix(data): normalize marital_status (feminine/legacy -> canonical) + drop dead legacy choices"
```

### Task 4: Frontend — `getErrorMessage` exibe erros por campo do DRF

**Files:**
- Modify: `frontend/lib/utils/error-handler.ts` (dentro de `getErrorMessage`, após o bloco `non_field_errors`, antes do check de network)
- Test: `frontend/lib/utils/__tests__/error-handler.test.ts`

- [ ] **Step 1: Testes (devem falhar)**

```ts
it('returns the first DRF field-level error as "field: message"', () => {
  const error = makeAxiosError(400, {
    marital_status: ["Value 'Solteira' is not a valid choice."],
  });
  expect(getErrorMessage(error)).toBe(
    "marital_status: Value 'Solteira' is not a valid choice."
  );
});

it('still prefers detail over field errors', () => {
  const error = makeAxiosError(400, { detail: 'Não encontrado.', campo: ['x'] });
  expect(getErrorMessage(error)).toBe('Não encontrado.');
});

it('falls back to the generic 400 message when body has no recognizable shape', () => {
  const error = makeAxiosError(400, {});
  expect(getErrorMessage(error)).toBe('Dados inválidos. Verifique os campos.');
});
```

(`makeAxiosError` — seguir o helper/padrão já usado nos testes existentes do arquivo.)

- [ ] **Step 2: Implementar**

```ts
// Format: { field: ["msg", ...] } (DRF field-level validation)
for (const [field, value] of Object.entries(responseData)) {
  if (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((m): m is string => typeof m === 'string')
  ) {
    return `${field}: ${value.join(', ')}`;
  }
}
```

- [ ] **Step 3: Rodar**

Run: `cd frontend && npm run test:unit -- error-handler` → PASS; `npm run lint && npm run type-check` → 0 erros/warnings.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/utils/error-handler.ts frontend/lib/utils/__tests__/error-handler.test.ts
git commit -m "fix(frontend): surface DRF field-level errors in getErrorMessage"
```

### Task 5: Gate, PR e deploy

- [ ] **Step 1: Gate backend (escopado nos arquivos editados + regressão dirigida)**

```bash
ruff check && ruff format --check && mypy core/ && pyright
python -m pytest tests/unit/test_exceptions.py tests/integration/test_exception_handler.py tests/unit/test_migrations_marital_status.py tests/integration/test_tenant_crud.py -p no:xdist
```
Zero erros e zero warnings. (Suite cheia tem flakiness pré-existente — regressão dirigida conforme roadmap.)

- [ ] **Step 2: Gate frontend**

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

- [ ] **Step 3: PR para `master`** (`commit-commands:commit-push-pr`). Nota de ordem: `chore/security-p0-p1-hardening` está aberta e também toca `core/serializers.py`/settings — quem entrar por último rebaseia (conflitos triviais).

- [ ] **Step 4: Deploy + verificação em prod (runbook)**

1. **Backup prod**: `python scripts/backup_db.py` apontando para prod (regra CRITICAL — há data migration).
2. Merge → Render deploya `master` (migrate roda no deploy; a migration normaliza ids 2, 4, 7 em prod).
3. Verificar o caso do incidente: Locações → Apto 112 → editar **Dia de Vencimento** → Atualizar → sucesso (200 no `PATCH /api/tenants/7/`).
4. Corrigir manualmente via UI os registros ambíguos (agora o erro 400 aponta o campo; a edição pelo form passa porque o valor novo substitui o inválido):

| Tenant | Corrigir | Fonte do valor correto |
| --- | --- | --- |
| 35 | `marital_status` ('-') e `phone` ('-') | cadastro real do inquilino |
| 40 | `due_day` (860) | contrato/lease do inquilino |
| 44, 45, 46 | `phone` (sem DDD) | adicionar DDD real (provável 51 — confirmar) |
| 11, 24, 27, 32 | `cpf_cnpj` (dígito verificador errado) | documento físico/foto do CPF |

5. Sanidade pós-correção (Supabase MCP, read-only): repetir `SELECT id, marital_status, phone, due_day FROM core_tenant WHERE is_deleted = false AND (marital_status NOT IN (<choices vigentes>) OR due_day > 31);` → 0 linhas (CPFs conferidos à parte).

> **Revisão completa dos dados (2026-06-11, prod vivo, validadores reais via Django shell):** os 12 tenants da tabela acima são **todos** os registros inválidos — nenhum outro tenant (ativo ou deletado) nem dependente falha validação. Observações cosméticas que NÃO bloqueiam (escopo P2.4): CPFs com formatação fora do padrão mas checksum válido (ids 30 `023.101-466-09`, 47 `066.486.077.00`, 43 sem máscara); `profession` placeholder `-`/`---` (ids 16, 21, 24, 35, 66, 67).

## Issue 2 (relacionada, NÃO duplicar aqui) — `generate_contract` 502

O 502 de 10/jun 15:25 (`API Proxy Error: TypeError: fetch failed`) é **evidência pré-fix**: `002eb85` (strip de headers hop-by-hop no proxy — undici rejeita `transfer-encoding`) foi commitado 8 min DEPOIS desse log, e o deploy do Render é de 11/jun. Plano próprio já existe: `docs/plans/2026-06-09-contract-pdf-prod-fix-plan.md`. Pendências de lá (não deste plano):

1. Item manual da Fase 2: start command do Render → `gunicorn --workers 1 --threads 4 --timeout 180` (sem isso, worker timeout de 30s mata o Chromium in-request).
2. Re-testar `generate_contract` em prod observando logs/memória do Render: sucesso = 200; `WORKER TIMEOUT` = aplicar o start command; OOM = escalar para Fase 3 (broker real + worker dedicado); 502 instantâneo (<2s) = rejeição de fetch remanescente.

## Constraints

- NÃO usar `# noqa` / `# type: ignore` / `eslint-disable`.
- NÃO normalizar/alterar CPF-CNPJ (escopo do P2.4); NÃO mexer na unicidade.
- NÃO alterar o fluxo do `LeaseFormModal` (PATCH cru vs `change_due_date` é P4.x).
- NÃO afrouxar `full_clean` (sem `exclude`); NÃO adicionar `'Solteira'`/`'-'` às choices.
- NÃO editar migrations existentes — só a nova (hooks bloqueiam).
- Toda mudança de modelo aqui é `AlterField` de choices (sem DDL real) — sem passo de RLS (nenhuma tabela nova).

## Critérios de aceite

- [ ] `PATCH /api/tenants/{id}/ {"due_day": N}` numa linha com dado armazenado inválido retorna **400 com o campo nomeado** (teste de integração prova; era 500).
- [ ] `PATCH /api/leases/{id}/` com linha inválida armazenada retorna 400 (não 500).
- [ ] Após `migrate`: zero linhas com `marital_status` fora das choices vigentes (local; prod após deploy).
- [ ] Choices legadas mortas removidas; nenhuma referência a valores legados em frontend/mobile (grep limpo ou exceção documentada).
- [ ] `getErrorMessage` exibe `campo: mensagem` para erro de campo DRF (teste Vitest).
- [ ] Gates backend e frontend: zero erros e zero warnings.
- [ ] Em prod: edição do dia de vencimento do Apto 112 funciona; os 9 registros do runbook corrigidos via UI.
