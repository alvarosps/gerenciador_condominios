# Sessão 52 — Backend: endpoint transacional `POST /api/onboarding/tenant-lease/`

> **Feature**: Fluxo "Novo inquilino + contrato" (web) — `docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
> **Sessões**: 51 → **52** → (53 ‖) → 54 → 55. Esta cria o **service + serializer de entrada + view + rota** que criam **inquilino + contrato numa transação atômica**, reusando os serializers reais (corrigidos na S51).
> **Depende de**: **S51** (disponibilidade de apto em `LeaseSerializer.validate`; `tenant._created_dependents`; guard de locador). **Se a S51 não estiver concluída, PARE.**
> **Branch**: `feat/tenant-lease-onboarding`.

---

## Contexto

Ler antes de codar:
- **Design doc** (ler §4.1, §4.2, §5 G1/G3/G4/G5, §6 erros, §7 testes): `@docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado**: `@prompts/SESSION_STATE.md` (ler contratos cross-session da S51)
- **Regras**: `CLAUDE.md`, `.claude/rules/{architecture,coding-standards,design-principles,security}.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha)

| Padrão | Local | Por quê |
|--------|-------|---------|
| Service com `transaction.atomic` + ORM | `core/services/lease_service.py` (`transfer_lease`/`terminate_lease`) | Forma do service stateless; `transaction.atomic()`; raise de erro de negócio. |
| `TenantSerializer` (create/update + dependents + `_created_dependents`) | `core/serializers.py:252-316` (S51 add `_created_dependents`) | Reusado pelo service p/ validar+persistir inquilino. |
| `LeaseSerializer` (validate c/ disponibilidade S51, create deriva rental_value) | `core/serializers.py:344-479` | Reusado p/ validar+persistir contrato; já injeta `responsible_tenant_id`/`tenant_ids`. |
| `Lease.UniqueConstraint` + `select_for_update` alvo | `core/models.py:733-736` | Lock do apto na corrida; `Apartment` é o alvo do `select_for_update`. |
| ViewSet/APIView + permissão admin | `core/views.py` (uso de `IsAdminUser`/`ReadOnlyForNonAdmin`) e `core/permissions.py` | `TenantLeaseOnboardingView` usa `IsAdminUser` (escrita de inquilino/contrato é admin-only). |
| Auditoria via `serializer.save(created_by=user)` | `core/viewsets/rule_views.py:72` | Service passa `created_by`/`updated_by` no `save()`. |
| Registro de rota | `core/urls.py` (router + `path(...)` custom) | Registrar a rota custom (não-router) do onboarding. |
| Testes de API (DB real, sem mock interno) | `tests/integration/test_finances_installments_employee_api.py` (existente) | Estilo de teste de integração (auth admin, status, payload). |

---

## Escopo

### Arquivos a criar
- `core/services/tenant_onboarding_service.py` — `TenantOnboardingService.onboard(...)`.
- `core/viewsets/onboarding_views.py` — `TenantLeaseOnboardingView(APIView)`.
- `tests/integration/test_onboarding_api.py` — testes de API.
- `tests/unit/test_tenant_onboarding_service.py` — testes do service (rollback, residente).

### Arquivos a modificar
- `core/serializers.py` — adicionar `TenantLeaseOnboardingSerializer` (valida shape: `tenant`, `lease`, `resident_dependent`, `resident_dependent_id`).
- `core/viewsets/__init__.py` — exportar `TenantLeaseOnboardingView`.
- `core/urls.py` — `path("onboarding/tenant-lease/", TenantLeaseOnboardingView.as_view(), name="tenant-lease-onboarding")`.

### NÃO fazer
- **NÃO** gerar PDF aqui (passo opcional separado — S55 reusa `generate_contract`).
- **NÃO** criar tabela/migração/RLS (sem model novo).
- **NÃO** impor "1 contrato ativo por inquilino" (design §2 — fora de escopo; constraint de apto cobre o banco).
- **NÃO** frontend. Sem `# noqa`/`# type: ignore`/`from __future__`/`TYPE_CHECKING`/re-export.

---

## Especificação

### Contrato da API (AUTORITATIVO — frontend S54 consome verbatim)
**Rota**: `POST /api/onboarding/tenant-lease/` · **Permissão**: `IsAdminUser` · **Auth**: JWT (não está na lista de isenção).

**Request body:**
```jsonc
{
  "tenant": { /* campos de escrita do TenantSerializer; "id" OPCIONAL (inquilino existente) */ },
  "lease":  { /* campos de escrita do LeaseSerializer, SEM responsible_tenant_id e SEM tenant_ids */ },
  "resident_dependent":    { "name": "...", "phone": "...", "cpf_cnpj": "" },  // opcional: 2º ocupante NOVO
  "resident_dependent_id": 123                                                 // opcional: 2º ocupante EXISTENTE
}
```
- `resident_dependent` e `resident_dependent_id` são **mutuamente exclusivos**; ambos ausentes ⇒ contrato de 1 inquilino (ou 2 sem dependente residente, conforme `lease.number_of_tenants`).

**Response 201:**
```jsonc
{ "tenant": { /* TenantSerializer */ }, "lease": { /* LeaseSerializer */ } }
```
**Erros**: `400 {"tenant": {...}}` ou `400 {"lease": {...}}` (namespeado) · `403` não-admin · `401` sem token.

### `TenantLeaseOnboardingSerializer` (entrada — valida só estrutura)
- `tenant = serializers.DictField()` (obrigatório) — pode conter `id`.
- `lease = serializers.DictField()` (obrigatório).
- `resident_dependent = serializers.DictField(required=False)`.
- `resident_dependent_id = serializers.IntegerField(required=False)`.
- `validate()`: rejeitar `resident_dependent` **e** `resident_dependent_id` juntos (PT); rejeitar `responsible_tenant_id`/`tenant_ids` presentes em `lease` (PT — "definidos pelo servidor"). Validação profunda de campos é delegada aos serializers reais dentro do service.

### `TenantOnboardingService.onboard(...)`
```python
@staticmethod
@transaction.atomic
def onboard(*, tenant_payload: dict, lease_payload: dict,
            resident_dependent: dict | None, resident_dependent_id: int | None,
            user) -> tuple[Tenant, Lease]:
    # 1) lock + disponibilidade do apto (corrida) — select_for_update no Apartment
    apartment = Apartment.objects.select_for_update().get(pk=lease_payload["apartment_id"])
    # (a checagem determinística vive em LeaseSerializer.validate — S51; aqui o lock fecha a corrida)

    # 2) inquilino: criar OU atualizar parcial (id presente)
    tid = tenant_payload.get("id")
    if tid:
        tenant = Tenant.objects.get(pk=tid)            # manager padrão exclui soft-deleted; DoesNotExist -> 400 tenant
        ser = TenantSerializer(tenant, data=tenant_payload, partial=True)
    else:
        ser = TenantSerializer(data=tenant_payload)
    ser.is_valid(raise_exception=True)                 # erros -> {"tenant": ...} (ver view)
    tenant = ser.save(created_by=user, updated_by=user)

    # 3) dependente residente (2 inquilinos)
    resolved_resident_id = resident_dependent_id
    if resident_dependent and not resident_dependent_id:
        dep = Dependent.objects.create(tenant=tenant, created_by=user, updated_by=user, **resident_dependent)
        resolved_resident_id = dep.id
    # (se for residente EXISTENTE, valida-se via LeaseSerializer que ele pertence ao tenant)

    # 4) contrato
    lease_data = {**lease_payload,
                  "responsible_tenant_id": tenant.id,
                  "tenant_ids": [tenant.id],
                  "resident_dependent_id": resolved_resident_id}
    lease_ser = LeaseSerializer(data=lease_data)
    lease_ser.is_valid(raise_exception=True)            # erros -> {"lease": ...}
    lease = lease_ser.save(created_by=user, updated_by=user)
    return tenant, lease
```
- Envolver a criação do contrato com `except IntegrityError` → `raise serializers.ValidationError({"apartment": ["Este apartamento já possui um contrato ativo."]})` (fallback da corrida; G3).
- O `@transaction.atomic` garante rollback de **tudo** (inclusive edição do inquilino existente e o `Dependent` residente) se o contrato falhar (sem órfão).
- Imports diretos no topo (`from django.db import transaction, IntegrityError`; models; serializers; `rest_framework.serializers`). Sem `from __future__`.

### `TenantLeaseOnboardingView(APIView)`
- `permission_classes = [IsAdminUser]`.
- `post(self, request)`: valida com `TenantLeaseOnboardingSerializer`; chama o service com `user=request.user`; em sucesso `Response({"tenant": TenantSerializer(tenant).data, "lease": LeaseSerializer(lease).data}, status=201)`.
- **Namespacing de erro**: o service levanta `ValidationError` cujo detalhe deve cair sob `tenant` ou `lease`. Estratégia: o service envolve a validação do inquilino e a do contrato e re-levanta com a chave correta — ex.: capturar `ValidationError` do bloco do inquilino e `raise serializers.ValidationError({"tenant": exc.detail})`; idem `{"lease": exc.detail}` no bloco do contrato. A view deixa o handler padrão do DRF transformar em 400.

---

## TDD — Red → Green → Refactor → Verify

> **Mock policy**: DB real (`--reuse-db`); auth admin via fixture; `transaction.atomic()` ao asserir constraint. **Nada** de mock interno.

### 1. RED — testes primeiro

#### `tests/integration/test_onboarding_api.py` (auth admin salvo onde indicado)
- [ ] **Sucesso inquilino novo**: POST com `tenant`(novo)+`lease`(1 inquilino) → 201; `Tenant` e `Lease` criados, `lease.responsible_tenant_id == tenant.id`, `tenant.id in lease.tenants`; response tem `{tenant, lease}`.
- [ ] **Sucesso inquilino existente + edição**: `tenant` com `id` e um campo alterado → 201; inquilino atualizado; novo `Lease` ligado.
- [ ] **Existente sem edição** (mesmos dados) → 201.
- [ ] **2 inquilinos, residente NOVO**: `lease.number_of_tenants=2` + `resident_dependent` → 201; `Dependent` criado no `tenant`, `lease.resident_dependent_id` setado, `resident_dependent.tenant_id == tenant.id`.
- [ ] **2 inquilinos, residente EXISTENTE**: inquilino existente com dependente, `resident_dependent_id` → 201.
- [ ] **Apartamento indisponível** (já tem contrato) → **400** com erro em `lease.apartment` (não 500).
- [ ] **CPF/CNPJ duplicado** → 400 em `tenant.cpf_cnpj`.
- [ ] **`number_of_tenants==2` sem `rental_value_double` no apto** → 400 em `lease`.
- [ ] **`resident_dependent` + `resident_dependent_id` juntos** → 400 (validação de shape).
- [ ] **`lease` com `responsible_tenant_id`/`tenant_ids`** → 400 (definidos pelo servidor).
- [ ] **Não-admin** (usuário comum autenticado) → 403. **Sem token** → 401.

#### `tests/unit/test_tenant_onboarding_service.py`
- [ ] **Rollback atômico**: `lease_payload` inválido (ex.: apto ocupado) → nenhuma `Tenant` nova persistida (`Tenant.objects.count()` inalterado) e, no caso existente, edição **não** aplicada.
- [ ] Residente novo: `Dependent` criado com `created_by`/`updated_by == user`.
- [ ] `id` de inquilino inexistente → erro namespeado `tenant`.

> Rodar (devem falhar):
> ```bash
> python -m pytest tests/integration/test_onboarding_api.py tests/unit/test_tenant_onboarding_service.py -q
> ```

### 2. GREEN — implementar service, serializer, view, rota, `__init__` export.

### 3. REFACTOR — DRY
- Reusar a constante de mensagem PT do apto ocupado da S51 (import, sem duplicar string).
- Namespacing de erro num único helper interno do service (`_reraise(scope, exc)`).
- Sem lógica de negócio na view (só orquestra serializer↔service↔response).

### 4. VERIFY — gate (escopo desta sessão)
```bash
python -m pytest tests/integration/test_onboarding_api.py tests/unit/test_tenant_onboarding_service.py -q
python -m pytest tests/unit/test_lease_serializer_availability.py tests/unit/test_tenant_serializer_dependent_capture.py -q  # regressão S51
ruff check core/services/tenant_onboarding_service.py core/viewsets/onboarding_views.py core/serializers.py core/urls.py core/viewsets/__init__.py tests/
ruff format --check core/services/tenant_onboarding_service.py core/viewsets/onboarding_views.py core/serializers.py core/urls.py core/viewsets/__init__.py tests/
mypy core/
pyright core/services/tenant_onboarding_service.py core/viewsets/onboarding_views.py core/serializers.py
```

---

## Constraints
- **View → Service → (Serializers/Models)**. Zero lógica de negócio na view; orquestração no service.
- **Atomicidade no service** (`@transaction.atomic` no método) — não depender de `ATOMIC_REQUESTS`. `select_for_update` no `Apartment` + `except IntegrityError` para a corrida.
- **Auditoria** via `serializer.save(created_by=user, updated_by=user)` (e no `Dependent.objects.create`).
- **Sem PDF, sem migração, sem RLS, sem regra "1 lease/inquilino"**.
- **Erros namespeados** `{"tenant"|"lease": ...}`; mensagens PT; `403`/`401` corretos.
- Sem suppressions; zero erros/warnings (ruff/mypy/pyright/pytest).

## Critérios de Aceite (binários)
- [ ] `POST /api/onboarding/tenant-lease/` cria inquilino (novo ou existente-editado) + contrato atomicamente; responde 201 `{tenant, lease}` ligados.
- [ ] 2 inquilinos: residente **novo** criado e ligado (`resident_dependent_id`), residente **existente** aceito; `resident_dependent` ⊕ `resident_dependent_id` exclusivos.
- [ ] Apto indisponível/CPF duplicado/`rental_value_double` ausente → **400 namespeado** (nunca 500). `responsible_tenant_id`/`tenant_ids` no `lease` → 400.
- [ ] Não-admin → 403; sem token → 401.
- [ ] Rollback atômico comprovado por teste (sem inquilino órfão; edição de existente revertida).
- [ ] Todos os testes verdes; regressão S51 verde; `ruff`/`mypy core/`/`pyright` limpos; sem suppressions.

## Handoff
1. Gate verde (acima).
2. Atualizar `prompts/SESSION_STATE.md` (S52 concluída; arquivos; **contrato da API verbatim** abaixo p/ S54).
3. `/audit` contra os Critérios de Aceite.
4. Commit:
   ```
   feat(core): transactional tenant+lease onboarding endpoint (service + serializer + view + route)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima: **S53** (extração DRY frontend + remoção email/phone_alternate) — pode rodar em paralelo a esta; e **S54** (wizard) que consome este contrato.

---

### Contrato cross-session AUTORITATIVO (S54 consome verbatim)
- **Rota**: `POST /api/onboarding/tenant-lease/` (admin-only).
- **Body**: `{ tenant{...,id?}, lease{... sem responsible_tenant_id/tenant_ids}, resident_dependent{name,phone,cpf_cnpj?}?, resident_dependent_id? }` (residente novo ⊕ existente).
- **201**: `{ tenant: <TenantSerializer>, lease: <LeaseSerializer> }`.
- **Erros**: `400 {tenant:{...}}` / `400 {lease:{...}}` (apto → `lease.apartment`); `403`/`401`.
- O servidor injeta `responsible_tenant_id`/`tenant_ids`; o cliente **não** os envia.
