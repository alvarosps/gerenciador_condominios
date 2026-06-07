# Sessão 42 — Backend: serializers/viewsets/ações para `InstallmentPlan`/`Installment`/`Employee`

> **Feature**: Condomínio Finance (módulo financeiro do condomínio — saídas/saldo/reserva/distribuição)
> **Sessões da Fase 3 (Parcelas + Folha)**: 41 → 42 → 43 (esta é a **42**, camada de API).
> A Sessão 41 entregou os **models + serviços** da Fase 3 (`InstallmentPlan`, `Installment`, `Employee`,
> `InstallmentPlanService.convert_deferred`, extensão de `BillGenerationService.ensure_month_bills` com
> installment+folha, sync realizado, abatimento §4.6). Esta sessão **expõe via API**: serializers dual,
> viewsets CRUD com filtros, e as ações (`installment-plans/{id}/convert_deferred`, CRUD de `employees`,
> `installments` read/edit do schedule). **Sem frontend** (Sessão 43). **Sem lógica de negócio nova** —
> os viewsets/ações **delegam** aos serviços da Sessão 41.

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §5.2 «App finances» inteira, §8 «serviços», §9 «API», §4.6 abatimento, §11 cache,
  §12 gate, §18 «Parcelas» + «Folha»)**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE):
  `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`,
  `.claude/rules/security.md`, `.claude/rules/design-principles.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Serializer dual com nested-read + `_id`-write + nulável** | `core/serializers.py:772-846` (`ExpenseSerializer`: `person`/`person_id`, `credit_card`/`credit_card_id`, `building`/`building_id`, `category`/`category_id`, `installments = …(many=True, read_only=True)`) | Modelo EXATO para `InstallmentPlanSerializer` (`category`/`category_id`, `building`/`building_id`, `linked_billing_account`/`_id`, nested `installments`) e `EmployeeSerializer` (`person`/`person_id`, `lease`/`lease_id`) |
| **Serializer filho (nested) com `SerializerMethodField` + read-only** | `core/serializers.py:741-769` (`ExpenseInstallmentSerializer`: `is_overdue` method, `read_only_fields=["id"]`) | Modelo para `InstallmentSerializer` (campos `number`/`due_date`/`amount`; `amount` é o **schedule** editável; ver §"`installments` é read+edit do schedule") |
| **FK simples nested-read + `_id`-write** | `core/serializers.py:688-708` (`CreditCardSerializer`: `person`/`person_id` via `PrimaryKeyRelatedField(source="person", write_only=True)`) | Forma canônica de um par FK read/write |
| **`PrimaryKeyRelatedField` self-FK / nulável** | `core/serializers.py:713-734` (`ExpenseCategorySerializer`: `parent_id` `allow_null` + `subcategories` read-only) | `Category` self-FK e FKs nuláveis do `finances` |
| **ViewSet CRUD com `get_queryset` + `select_related`/`prefetch_related` + filtros por query param** | `core/viewsets/financial_views.py:294-333` (`ExpenseInstallmentViewSet.get_queryset`) e `:137-194` (`ExpenseViewSet` com helpers `_apply_*_filters`) | Estrutura dos 3 viewsets desta sessão |
| **`@action(detail=True)` atômico que delega a serviço + `select_for_update` + 400/serializa** | `core/viewsets/financial_views.py:196-207` (`mark_paid`) e `:263-291` (`rebuild` → `ExpenseService.rebuild_installments`) | Modelo EXATO para `installment-plans/{id}/convert_deferred` (delega a `InstallmentPlanService.convert_deferred`) |
| **`@action(detail=False)` com validação PT + `date.fromisoformat` + 400** | `core/viewsets/financial_views.py:603-652` (`bulk_configure`) e `:654-687` (`person_month_total`) | Validação de params, mensagens PT, `reference_month.day == 1` guard |
| **ViewSet sem queryset de classe (define em `get_queryset`) com `permission_classes=[FinancialReadOnly]`** | `core/viewsets/financial_views.py:56-90` (`PersonViewSet`/`CreditCardViewSet`) | Permissão + filtros |
| **Registro de viewsets no router + import** | `core/urls.py:15-39` (bloco `from .viewsets import (...)`) e `:58-82` (`router.register(r"…", …ViewSet, basename="…")`) | Onde registrar as 3 novas rotas namespaced `/api/finances/...` |
| **Export de viewsets no pacote** | `core/viewsets/__init__.py` (padrão `from .web_push_views import WebPushViewSet` + `__all__`) | Exportar os 3 viewsets do `finances` (import direto da fonte, sem re-export/barrel novo) |
| **Pagination padrão** | `core/pagination.py:7` (`CustomPageNumberPagination`) | `pagination_class` (lista paginada com `results`) |
| **Permissão financeira (autenticado lê, `is_staff` escreve)** | `core/permissions.py:107-121` (`FinancialReadOnly`) | `permission_classes` de todos os viewsets desta sessão |
| **Teste de integração CRUD + matriz de permissão** | `tests/integration/test_financial_permissions.py:16-58` (listas `FINANCIAL_WRITE_ENDPOINTS`/`FINANCIAL_READ_ENDPOINTS`, parametrização não-admin 403 / admin ≠403 / read 200 / anon 401) | Modelo da matriz de permissão para as rotas novas |
| **Teste de integração com fixtures de domínio + factories** | `tests/integration/test_income_payment_api.py:1-90` | Estrutura de arquivo, imports de `tests/factories`, fixtures |
| **Fixtures de client/usuário** | `tests/conftest.py:71` (`api_client`), `:84` (`admin_user`), `:99` (`regular_user`), `:114` (`authenticated_api_client`), `:123` (`regular_authenticated_api_client`) | Clients para a matriz de permissão |

### Artefatos da Sessão 41 que esta sessão CONSOME (não recriar — ler do `SESSION_STATE.md` atualizado)

- **Models** `finances/models.py`: `InstallmentPlan`, `Installment`, `Employee` (campos conforme design
  §5.2). `InstallmentPlan`/`Installment`/`Employee` = `(AuditMixin, SoftDeleteMixin, models.Model)` +
  managers duplos (`objects` exclui soft-deleted, `all_objects` inclui).
- **Serviços** `finances/services/`: `InstallmentPlanService.convert_deferred(...)` (atômico; fecha o item
  deferido → cria `InstallmentPlan` com `total == valor deferido`). **A ação `convert_deferred` desta
  sessão APENAS chama esse serviço** — nenhuma lógica de conversão aqui.
- **Factories** `tests/factories.py`: `make_installment_plan(...)`, `make_installment(...)`,
  `make_employee(...)` (+ `make_condominium`, `make_building(condominium=...)` da Fase 1a). Usar essas;
  **não** instanciar models à mão (`tests/CLAUDE.md`).

> Os nomes/caminhos/campos acima são o **contrato cross-session** da Fase 3. **Verbatim** — não derivar
> nem renomear. Se algum diferir do `SESSION_STATE.md` real, **o `SESSION_STATE.md` prevalece** (parar e
> alinhar antes de codar).

---

## Escopo

### Arquivos a criar
- `finances/serializers.py` — **estender** (já existe da Fase 2 com `Category`/`BillingAccount`/`Bill`/…)
  com `InstallmentPlanSerializer`, `InstallmentSerializer`, `EmployeeSerializer`. *(Se a Fase 2 não criou
  o arquivo, criá-lo agora seguindo o exemplar `core/serializers.py`.)*
- `finances/viewsets.py` (ou pacote `finances/viewsets/` — **seguir a convenção que a Fase 2 já
  adotou**) — `InstallmentPlanViewSet`, `InstallmentViewSet`, `EmployeeViewSet`.
- `tests/integration/test_finances_installments_employee_api.py` — testes de integração (CRUD + ações +
  filtros + paginação + dual serializer + soft-delete + matriz `FinancialReadOnly`).

### Arquivos a modificar
- `finances/urls.py` — registrar `installment-plans`, `installments`, `employees` no router namespaced
  (`/api/finances/...`). Seguir `core/urls.py:58-82`.
- `finances/viewsets/__init__.py` (se pacote) **ou** o `__init__` que exporta os viewsets — exportar os 3
  novos (import direto da fonte; **sem** re-export/barrel novo).
- `finances/signals.py` — **somente se necessário**: a Fase 2 já registrou `post_save`/`post_delete` em
  **todos** os models do `finances` invalidando `finance-*` (design §11, bloco único de constantes de
  prefixo). `InstallmentPlan`/`Installment`/`Employee` provavelmente **já** estão cobertos. Verificar; se
  algum dos 3 não estiver no conjunto de receivers, **adicionar** (sem duplicar prefixos, sem novo bloco
  de constantes). **Sem cache cross-app novo** (esse é da Fase 2/§11 — Apartment/Lease/RentAdjustment).

### NÃO fazer (pertence a outras sessões)
- **Nenhum** frontend, hook, query-key, schema Zod ou componente — **Sessão 43**.
- **Nenhuma** lógica de negócio: conversão de deferido, dedup de embutido, sync realizado×schedule,
  abatimento §4.6, geração de bills (`ensure_month_bills`) — **tudo na Sessão 41** (esta sessão **delega**).
- **Nenhum** model novo / migração / mudança de campo — models são da Sessão 41.
- **Nenhum** endpoint de **pagamento** de parcela (`pay`/`bulk_pay`) — pagamento é via `bills/{id}/pay`
  (Fase 2 / `BillPaymentService`), não em `installments`. Não duplicar.
- **Nenhum** serializer/viewset de `Bill`/`BillLineItem`/`Category`/`BillingAccount`/`Payment`/`Reserve`/
  `IncomeEntry`/`CondoMonthClose` — esses são de outras fases (2/4).
- **Nenhuma** action de dashboard/cash-flow/distribuição (`finance-dashboard/*`, `finance-cash-flow/*`,
  `OwnerDistributionService`) — Fases 4/5/6.
- **Sem** seed de dados/categorias (design §13 — o admin cria tudo).
- **Sem** novo bloco de constantes de cache nem receivers cross-app (Apartment/Lease) — Fase 2/§11.

---

## Especificação

DRF `ModelViewSet` + `FinancialReadOnly` (autenticado lê, `is_staff` escreve);
`pagination_class = CustomPageNumberPagination`. Serializers **dual** (nested read / `_id` write);
`Decimal` serializado como string; validação e mensagens ao usuário em **PT**, logs/dev em **EN**;
`start_due_date`/`due_date` são `date`; ações que delegam a serviço usam `@transaction.atomic` +
`select_for_update` **dentro do serviço** (a Sessão 41 já fez isso — a ação não re-transaciona a lógica,
só carrega o objeto e chama o serviço). Direção de dependência: viewset → service → model (nunca o
inverso); serializer → model (nunca service).

### 9.1 `InstallmentPlanSerializer` (dual, nested `installments` read-only)

```python
class InstallmentPlanSerializer(serializers.ModelSerializer):
    category = FinanceCategorySerializer(read_only=True)              # nested read (da Fase 2)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    building = BuildingSerializer(read_only=True)                     # core BuildingSerializer
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.all(), source="building",
        write_only=True, required=False, allow_null=True,            # nível-condomínio = null
    )
    linked_billing_account = BillingAccountSerializer(read_only=True) # nested read (da Fase 2)
    linked_billing_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BillingAccount.objects.all(), source="linked_billing_account",
        write_only=True, required=False, allow_null=True,            # só p/ embutido
    )
    installments = InstallmentSerializer(many=True, read_only=True)   # nested read-only
    # campos: description, total_amount, installment_count, start_due_date,
    #         default_due_day, lifecycle_state, embedded, created_at, updated_at
    # read_only_fields = ["id", "created_at", "updated_at"]
```

- `total_amount` Decimal→string. `lifecycle_state ∈ {active, paid, deferred, canceled}` (string do model).
- **Não** criar `Installment`s via nested writable no serializer — a materialização das parcelas é do
  serviço (Sessão 41 / `ensure_month_bills`). O serializer escreve só o **plano**.

### 9.2 `InstallmentSerializer` (filho; `amount` = schedule editável)

```python
class InstallmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()  # espelha ExpenseInstallmentSerializer:760
    # campos: id, plan (PK), number, due_date, amount, is_overdue
    # read_only_fields = ["id", "plan", "number"]   # number/plan fixados na materialização
```

- **`installments` é read + edit do schedule** (ver §abaixo). `amount` é o **schedule** (projeção) — o
  admin pode **ajustar** o valor planejado de uma parcela futura via `PATCH /api/finances/installments/{id}/`.
  **O realizado** (`BillLineItem.amount`) e o sync realizado×schedule são da Sessão 41 — esta sessão
  **não** mexe em `BillLineItem`. Editar `amount` aqui altera **apenas** o schedule da `Installment`.
- `is_overdue = not <paga> and due_date < hoje` — usar o helper TZ `America/Sao_Paulo` da Fase 1a (NÃO
  `timezone.now().date()` direto; "paga" deriva da existência de `Bill`/realizado conforme o model da
  Sessão 41 — se o model não expõe um campo de pago na `Installment`, computar `is_overdue` apenas por
  `due_date < hoje` é incorreto: **ler o model da Sessão 41** e usar o critério que ele define; se não
  houver semântica de "paga" na `Installment`, expor `is_overdue` por `due_date < hoje` E o plano
  `lifecycle_state == active`).

### 9.3 `EmployeeSerializer` (dual; `person`/`lease` nuláveis)

```python
class EmployeeSerializer(serializers.ModelSerializer):
    person = PersonSimpleSerializer(read_only=True)                  # core PersonSimpleSerializer
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person",
        write_only=True, required=False, allow_null=True,
    )
    lease = LeaseSerializer(read_only=True)                          # core LeaseSerializer (ou Summary)
    lease_id = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.all(), source="lease",
        write_only=True, required=False, allow_null=True,
    )
    # campos: name, role, payment_type, base_salary, default_due_day,
    #         is_active, notes, created_at, updated_at
    # read_only_fields = ["id", "created_at", "updated_at"]
```

- `payment_type ∈ {fixed, variable, mixed}`. `base_salary` nulável/0 (variável-only = Raymel → `null`).
- **Não** validar aqui o invariante §4.6 (abatimento = `effective_rental_value`) — esse `clean()`/serviço é
  da Sessão 41. O serializer só expõe os campos.

### 9.4 `InstallmentPlanViewSet`

- `serializer_class = InstallmentPlanSerializer`, `permission_classes = [FinancialReadOnly]`,
  `pagination_class = CustomPageNumberPagination`.
- `get_queryset()`: `InstallmentPlan.objects.select_related("category", "building",
  "linked_billing_account").prefetch_related("installments")`. Filtros por query param (espelhar
  `ExpenseInstallmentViewSet.get_queryset`): `condominium_id`, `building_id`, `category_id`,
  `lifecycle_state`, `embedded` (bool `lower()=="true"`). **Default queryset já exclui soft-deleted**
  (manager `objects`) — não usar `all_objects`.
- **Ação `@action(detail=True, methods=["post"]) convert_deferred`** (espelhar `rebuild` em `:263-291`):
  - Carrega o plano-alvo? **Não** — `convert_deferred` opera sobre o **item deferido** (IPTU anual: pode
    ser um `Bill`/`BillingAccount` deferido conforme a Sessão 41). **Ler a assinatura real de
    `InstallmentPlanService.convert_deferred` no `SESSION_STATE.md`/código da Sessão 41** e montar a ação
    em torno dela: validar params do `request.data` (mensagens PT, 400 em ausência/inválido), chamar o
    serviço, e **serializar o `InstallmentPlan` resultante** com `InstallmentPlanSerializer` (201/200).
  - Passar `user=cast(User, request.user)` ao serviço (auditoria), como `rebuild` faz em `:287`.
  - **Não** re-implementar a atomicidade/lógica — o serviço já é `@transaction.atomic`.

### 9.5 `InstallmentViewSet`

- `serializer_class = InstallmentSerializer`, `permission_classes = [FinancialReadOnly]`, paginação.
- `get_queryset()`: `Installment.objects.select_related("plan", "plan__category")`. Filtros: `plan_id`,
  `due_date_from`/`due_date_to` (espelhar `:317-323`).
- **CRUD parcial:** list/retrieve (read) + `PATCH` para ajustar `amount`/`due_date` do **schedule**.
  `create`/`destroy` de `Installment` avulsa **não** são expostos aqui (parcelas nascem da materialização
  do plano — Sessão 41). Restringir `http_method_names` a `["get", "patch", "head", "options"]` no
  viewset (KISS — não expor POST/PUT/DELETE que não fazem sentido).

### 9.6 `EmployeeViewSet`

- `serializer_class = EmployeeSerializer`, `permission_classes = [FinancialReadOnly]`, paginação.
- `get_queryset()`: `Employee.objects.select_related("person", "lease",
  "lease__apartment", "lease__apartment__building")`. Filtros: `condominium_id`, `is_active` (bool),
  `payment_type`, `person_id`, `lease_id`. CRUD completo (`ModelViewSet`).
- **Fim de lease** (abatimento para quando `lease.is_deleted=True`) é detectado por `is_deleted` no
  serviço/folha (Sessão 41) — **não** filtrar `lease` por `is_deleted` aqui (o `Employee` continua
  existindo; só o abatimento na folha para). Não tocar nessa lógica.

### 9.7 URLs (namespaced)

Em `finances/urls.py` (router próprio do app, montado sob `/api/finances/`):
```python
router.register(r"installment-plans", InstallmentPlanViewSet, basename="finance-installment-plans")
router.register(r"installments", InstallmentViewSet, basename="finance-installments")
router.register(r"employees", EmployeeViewSet, basename="finance-employees")
```
Rotas finais: `/api/finances/installment-plans/`, `…/installment-plans/{id}/convert_deferred/`,
`/api/finances/installments/` (+ `{id}` PATCH), `/api/finances/employees/`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **apenas fronteiras externas**. Aqui **não há** fronteira
> externa a mockar além de `freezegun` para `is_overdue`. **NUNCA** mockar ORM, serializers,
> `InstallmentPlanService` nem qualquer serviço/model do `finances` ou `core`. Banco real (`--reuse-db`),
> dados via factories da Sessão 41. Testes de integração exercitam **view → serializer → service →
> model** (preferidos a unit — `tests/CLAUDE.md`).

### 1. RED — escrever os testes primeiro

Criar `tests/integration/test_finances_installments_employee_api.py` (`@pytest.mark.django_db`,
`@pytest.mark.integration`). Usar `authenticated_api_client` (admin), `regular_authenticated_api_client`
(não-admin) e `api_client` (anônimo) de `conftest.py`; factories `make_condominium`,
`make_building(condominium=...)`, `make_installment_plan`, `make_installment`, `make_employee`,
`make_person`, `make_lease` da Sessão 41/Fase 1a. Cobrir, no mínimo:

**`installment-plans` CRUD + dual serializer**
- [ ] `POST /api/finances/installment-plans/` (admin) com `category_id`/`building_id`/`description`/
  `total_amount`/`installment_count`/`start_due_date`/`default_due_day` cria → 201; resposta tem
  `category`/`building` **nested** (read) e **não** os `_id`; `total_amount` é **string**.
- [ ] `building_id=null` (nível-condomínio) aceito → 201, `building` null na resposta.
- [ ] `linked_billing_account_id` setado (embutido) → 201, `linked_billing_account` nested na resposta;
  ausência aceita (avulso) → `embedded=false`/`linked_billing_account=null`.
- [ ] `GET /api/finances/installment-plans/` lista **paginada** (envelope `results`), filtros
  `building_id`/`category_id`/`lifecycle_state`/`embedded` reduzem corretamente.
- [ ] `GET …/{id}/` retorna `installments` **nested** (read-only) ordenadas por `number`.
- [ ] `PATCH …/{id}/` (admin) altera `description`/`lifecycle_state` → 200.
- [ ] `DELETE …/{id}/` (admin) **soft-delete**: some de `objects`/da listagem; `all_objects` ainda acha
  com `is_deleted=True`. *(§18 «soft-deleted Bill/Payment excluído dos totais» — análogo p/ plan.)*

**`installment-plans/{id}/convert_deferred` (delega ao serviço da S41)**
- [ ] item deferido → `POST …/{id}/convert_deferred/` (admin) com os params reais da assinatura S41 →
  retorna o `InstallmentPlan` resultante serializado; `total_amount` do plano **== valor deferido**
  (§18 «`convert_deferred` sem duplicar/perder»; o item deferido vira estado terminal — assert que o
  item de origem ficou no estado terminal definido pela S41 e **fora** de futuras somas/listagens
  ativas). *(A asserção numérica de "não duplica/não some" exercita o serviço real — sem mock.)*
- [ ] params ausentes/inválidos → **400** com mensagem **PT** (sem 500).
- [ ] não-admin → **403**; anônimo → **401**.

**`installments` (read + edit do schedule)**
- [ ] materializar um plano (via `make_installment` da S41) → `GET /api/finances/installments/?plan_id=…`
  lista paginada filtrada por plano; `due_date_from`/`due_date_to` filtram.
- [ ] `PATCH /api/finances/installments/{id}/` (admin) altera **`amount`** (schedule) → 200; resposta
  reflete o novo `amount` (string Decimal). *(§18 «realizado ≠ schedule» — esta sessão edita só o
  schedule; o sync com realizado é da S41 e NÃO é exercitado/alterado aqui.)*
- [ ] `POST`/`DELETE` em `installments` → **405 Method Not Allowed** (não expostos; só GET/PATCH).
- [ ] `is_overdue` correto sob `@freeze_time` (parcela vencida não-paga → `True`; futura → `False`),
  consistente com o helper TZ SP (§18 «virada de mês na TZ SP»: parcela vencendo na virada não vira
  overdue espúrio em UTC).

**`employees` CRUD + dual serializer**
- [ ] `POST /api/finances/employees/` (admin) `payment_type="mixed"` com `person_id`/`lease_id`
  (Rosa-like) → 201; `person`/`lease` nested na resposta; `base_salary` string.
- [ ] `payment_type="variable"`, `base_salary=null` (Raymel-like) → 201 (§18 «variável-only»).
- [ ] `person_id`/`lease_id` ausentes (autônomo sem vínculo) → 201, ambos null.
- [ ] `GET /api/finances/employees/` paginada; filtros `is_active`/`payment_type`/`person_id`/`lease_id`.
- [ ] `PATCH …/{id}/` altera `is_active`/`role` → 200; `DELETE …/{id}/` soft-delete (some da listagem,
  `all_objects` acha).

**Matriz `FinancialReadOnly` (espelhar `test_financial_permissions.py:16-58`)**
- [ ] não-admin: `GET` nas 3 rotas → **200**; `POST`/`PATCH`/`DELETE`/`convert_deferred` → **403**.
- [ ] admin: write passa do gate de permissão (≠403 — 201/200/400 aceitáveis).
- [ ] anônimo: qualquer método → **401**.

**Cache (signals)**
- [ ] após `POST`/`PATCH`/`DELETE` em `installment-plans`/`employees`, os caches `finance-*` são
  invalidados (assertar via `cache`/`CacheManager` que a chave/glob `finance-dashboard`/`finance-cash-flow`/
  `finance-projection` foi limpa — se a Fase 2 já cobre os 3 models, este teste **confirma** a cobertura;
  se faltava algum, o teste guia a adição em `finances/signals.py`). *(§18 cross-app cache — porção do
  `finances` próprio.)*

> Rodar (devem **falhar** — viewsets/serializers/rotas ainda não existem):
> ```bash
> python -m pytest tests/integration/test_finances_installments_employee_api.py -q
> ```

### 2. GREEN — implementar serializers, viewsets, rotas

Implementar `InstallmentPlanSerializer`/`InstallmentSerializer`/`EmployeeSerializer` (estendendo
`finances/serializers.py`), os 3 viewsets (`finances/viewsets`), registrar no `finances/urls.py` e
exportar no `__init__`. Ação `convert_deferred` **delega** a `InstallmentPlanService.convert_deferred`.
Verificar/estender `finances/signals.py` apenas se algum dos 3 models não estiver coberto. O **mínimo**
para os testes passarem. Rodar até verde:
```bash
python -m pytest tests/integration/test_finances_installments_employee_api.py -q
```

### 3. REFACTOR — DRY / Clean Code (sem mudar comportamento)

- Extrair helpers `_apply_*_filters` se um `get_queryset` ficar grande (espelhar `ExpenseViewSet:156-194`).
- Garantir que **nenhuma** lógica de negócio vazou para viewset/serializer (conversão/sync/abatimento ⇒
  serviço da S41). Viewsets finos; ações delegam.
- Sem duplicação do par dual entre os 3 serializers além do inevitável (cada um tem FKs distintas).

### 4. VERIFY — gate (escopo dos arquivos editados)

> Suíte completa tem problemas pré-existentes de xdist/Redis (memória do projeto) — rodar **scoped**.

```bash
ruff check finances/ tests/integration/test_finances_installments_employee_api.py
ruff format --check finances/ tests/integration/test_finances_installments_employee_api.py
mypy core/ finances/
pyright
python -m pytest tests/integration/test_finances_installments_employee_api.py -q
python -m pytest --cov=finances --cov-report=term-missing tests/integration/test_finances_installments_employee_api.py -q   # ≥90% nas linhas tocadas
```
Zero erros **e** zero warnings (Ruff, mypy, Pyright, pytest — `filterwarnings=error`). Cobertura
**≥90%** no `finances` (standalone) para os módulos desta sessão.

---

## Constraints

- **Direção de dependência**: viewset → service → model; serializer → model. **Nunca** serializer→service,
  nunca service→viewset. Lógica de negócio **só** em serviços (todos os da Fase 3 = Sessão 41).
- **Serializer dual obrigatório**: nested read + `_id` write (`PrimaryKeyRelatedField(source=…,
  write_only=True)`); FKs nuláveis com `required=False, allow_null=True`. **Sem** nested-writable de
  `Installment` no `InstallmentPlanSerializer` (parcelas nascem do serviço).
- **Soft-delete**: `DELETE` = soft (`instance.delete()`); querysets default usam `objects` (excluem
  deletados); testes validam com `all_objects`.
- **Decimal como string** na API; `start_due_date`/`due_date` `date`; mensagens ao usuário em **PT**,
  logs em **EN**.
- **`convert_deferred`** apenas **delega** ao serviço (atomicidade/`select_for_update` já no serviço);
  passar `user` para auditoria; serializar o resultado.
- **`installments`**: só `GET`/`PATCH` (schedule). **Não** expor `pay`/`bulk_pay` (pagamento é
  `bills/{id}/pay`, Fase 2). Sem POST/PUT/DELETE em `installments`.
- **Cache**: prefixos `finance-dashboard`/`finance-cash-flow`/`finance-projection` vêm do **bloco único
  de constantes** (design §11) — **não** redefinir. **Sem** receivers cross-app (Apartment/Lease) aqui.
- **Sem suppressions**: proibido `# noqa`, `# type: ignore`, `eslint-disable`. Corrigir o código de
  verdade. Tipos completos (mypy strict + Pyright strict).
- **Sem `from __future__ import annotations`** e **sem `if TYPE_CHECKING`** — importar tipos diretamente
  (`from django.db.models import QuerySet`, `from django.contrib.auth.models import User`, etc.).
- **Sem re-exports / barrel files / shims de compatibilidade.** `finances/viewsets/__init__` exporta só o
  que define; consumidores importam da fonte.
- **Sem model/migração/campo novo**; sem mexer em models/serviços da Sessão 41; sem frontend.
- **SOLID/DRY/KISS/YAGNI/Clean Code** (`.claude/rules/design-principles.md`) — refactor completo, sem
  workarounds, sem TODO/FIXME, todos os consumidores atualizados.

---

## Critérios de Aceite (binários)

- [ ] `finances/serializers.py` contém `InstallmentPlanSerializer` (dual: `category`/`category_id`,
  `building`/`building_id` nulável, `linked_billing_account`/`_id` nulável, `installments` nested
  read-only), `InstallmentSerializer` (`amount` schedule editável + `is_overdue`),
  `EmployeeSerializer` (dual: `person`/`person_id` nulável, `lease`/`lease_id` nulável).
- [ ] `finances/viewsets` contém `InstallmentPlanViewSet`, `InstallmentViewSet`, `EmployeeViewSet` com
  `FinancialReadOnly` + `CustomPageNumberPagination` + `get_queryset` com `select_related`/
  `prefetch_related` + filtros por query param.
- [ ] `InstallmentPlanViewSet.convert_deferred` (`@action detail=True POST`) **delega** a
  `InstallmentPlanService.convert_deferred`, valida params (PT/400), serializa o `InstallmentPlan`
  resultante; **nenhuma** lógica de conversão no viewset.
- [ ] `InstallmentViewSet` expõe **só** `GET`/`PATCH` (POST/PUT/DELETE → 405).
- [ ] Rotas registradas em `finances/urls.py`: `/api/finances/{installment-plans,installments,employees}/`
  (+ `installment-plans/{id}/convert_deferred/`); viewsets exportados no `__init__` (sem re-export novo).
- [ ] `finances/signals.py` cobre `InstallmentPlan`/`Installment`/`Employee` para invalidação `finance-*`
  (confirmado ou estendido sem duplicar prefixos).
- [ ] `tests/integration/test_finances_installments_employee_api.py` cobre: CRUD dos 3 recursos; dual
  serializer (nested read, `_id` write, Decimal string); paginação `results`; filtros;
  `convert_deferred` (valor preservado + estado terminal + 400 + 403/401); `installments` PATCH do
  schedule + 405 em POST/DELETE + `is_overdue` sob freeze; soft-delete (`objects` vs `all_objects`);
  matriz `FinancialReadOnly` (não-admin read 200 / write 403, admin ≠403, anon 401); invalidação de
  cache `finance-*`.
- [ ] `python -m pytest tests/integration/test_finances_installments_employee_api.py` passa **100%**.
- [ ] `ruff check && ruff format --check && mypy core/ finances/ && pyright` limpos nos arquivos tocados —
  **sem** `# noqa`/`# type: ignore`.
- [ ] Cobertura `--cov=finances` **≥90%** nas linhas desta sessão; zero warnings (`filterwarnings=error`).
- [ ] Nenhuma lógica de negócio em viewset/serializer; nenhum frontend; nenhum model/migração novo;
  nenhuma alteração nos models/serviços da Sessão 41.

---

## Handoff

1. Rodar e confirmar verde (escopo desta sessão):
   ```bash
   python -m pytest tests/integration/test_finances_installments_employee_api.py -q
   ruff check finances/ tests/integration/test_finances_installments_employee_api.py
   ruff format --check finances/ tests/integration/test_finances_installments_employee_api.py
   mypy core/ finances/
   pyright
   python -m pytest --cov=finances --cov-report=term-missing tests/integration/test_finances_installments_employee_api.py -q
   ```
2. Atualizar `prompts/SESSION_STATE.md` (somente a tabela de progresso/notas da feature — **não** mexer
   no que o orquestrador gerencia):
   - Marcar a Sessão 42 como **concluída**.
   - **Arquivos Criados**: `tests/integration/test_finances_installments_employee_api.py` (+ `finances/
     serializers.py`/`finances/viewsets*` se foram criados aqui).
   - **Arquivos Modificados**: `finances/serializers.py`, `finances/viewsets(/...)`, `finances/urls.py`,
     `finances/viewsets/__init__.py`, e `finances/signals.py` (se estendido).
   - **Contratos cross-session expostos** (verbatim para a Sessão 43 FE consumir):
     - Rotas: `/api/finances/installment-plans/` (+ `{id}/convert_deferred/`),
       `/api/finances/installments/` (GET/PATCH), `/api/finances/employees/`.
     - Shapes dual: `InstallmentPlanSerializer` (read nested `category`/`building`/`linked_billing_account`
       + `installments`; write `category_id`/`building_id`/`linked_billing_account_id`),
       `EmployeeSerializer` (read `person`/`lease`; write `person_id`/`lease_id`),
       `InstallmentSerializer` (`amount` schedule editável + `is_overdue`). Decimal = string;
       `lifecycle_state`/`payment_type` strings do model.
     - `convert_deferred` = POST detail que retorna o `InstallmentPlan` serializado (assinatura dos params
       herdada de `InstallmentPlanService.convert_deferred` da S41).
   - Nota: "Camada de API da Fase 3 (parcelas+folha); viewsets finos delegam à S41; `installments` só
     GET/PATCH (schedule); pagamento continua em `bills/{id}/pay` (Fase 2); cache `finance-*` confirmado/
     estendido; sem frontend (S43); sem lógica de negócio nova."
3. Rodar `/audit` (skill `audit`) contra esta seção de **Critérios de Aceite** e corrigir gaps antes de
   fechar a sessão.
4. Commitar (a partir de `master`, criar branch da feature se necessário):
   ```
   feat(finances): add API layer for installment plans, installments and employees (serializers + viewsets + convert_deferred action)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **43 — Frontend: telas/hooks de Parcelas + Folha** (lê o `SESSION_STATE.md`
   atualizado), consumindo as rotas/shapes acima via TanStack Query v5 (`useQuery` +
   `placeholderData: keepPreviousData`), Zod 4 + RHF, `useCrudPage`, query-keys centralizados,
   escrita gated em `is_staff`.
