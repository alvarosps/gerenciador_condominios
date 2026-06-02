# Sessão 22 — Backend: endpoints `rent_calendar` + `toggle_rent_payment`

> Parte da feature **Calendário de Controle de Aluguéis**. Sessões: `21` (service + DRY) → **`22` (endpoints)** → `23`/`24`/`25` (frontend + verificação final).

## Contexto

Ler **antes de tocar em código**:
- Design completo: @docs/plans/2026-06-02-rent-payment-calendar-design.md — focar em §4.3 (endpoints), §4.4 (regras do toggle), §4.5 (cálculo de stats), §3 (premissas A1–A5).
- Estado das sessões: @prompts/SESSION_STATE.md (confirmar que a sessão 21 está concluída — `RentScheduleService` existe e seus unit tests passam).
- Padrão de prompts: @prompts/00-prompt-standard.md.
- Regras do projeto: @CLAUDE.md, @.claude/rules/architecture.md, @.claude/rules/coding-standards.md, @.claude/rules/testing.md, @.claude/rules/design-principles.md, @.claude/rules/api-design.md, @.claude/rules/security.md.

Exemplares concretos (ler estes — exemplar > descrição):
- **`DashboardViewSet` + padrão `@action`**: `core/views.py:578-789`. Estrutura do ViewSet (`viewsets.ViewSet`, `permission_classes = [IsAdminUser]` em `:598`), actions GET (`late_payment_summary` `:668-696`, `building_statistics` `:644-666`) e a action POST a unificar mais tarde (`mark_rent_paid` `:722-775`).
- **Imports já presentes no topo de `core/views.py`**: `:1-37` — `status`, `viewsets`, `action`, `Request`, `Response`, `IsAdminUser`, `Lease`, `RentPayment`, `DashboardService`, `cast`, `User`, `timezone`, `Decimal`/`InvalidOperation`, `date`.
- **Registro do router**: `core/urls.py:51` — `router.register(r"dashboard", DashboardViewSet, basename="dashboard")` (já registrado; as novas actions são expostas automaticamente, **nada a alterar** em `urls.py`).
- **Permissão admin-only**: `core/permissions.py:32-44` (`IsAdminUser` — `is_staff or is_superuser`).
- **API do `RentScheduleService`** (consumir, produzido na sessão 21): `core/services/rent_schedule_service.py` — métodos `get_month_schedule(year, month, building_id=None) -> dict`, `toggle_payment(lease_id, reference_month: date, user) -> dict` (ver assinaturas no design §4.1).
- **Exemplar de teste de integração do dashboard/daily-control**: `tests/integration/test_daily_control_api.py:78-255` — classes por endpoint, fixtures com `admin_user`, asserts de shape, casos 400/401/404, uso de `authenticated_api_client`.
- **Fixtures de auth/clientes**: `tests/conftest.py` — `api_client` (`:53`), `admin_user` (`:66`), `regular_user` (`:81`), `authenticated_api_client` (`:96`, admin), `regular_authenticated_api_client` (`:104`, não-admin), `enable_db_access_for_all_tests` (`:113`, autouse).
- **Helpers `model-bakery` para Building/Apartment/Tenant/Lease**: `tests/integration/test_rent_adjustment.py:42-100` (`_make_building`, `_make_apartment`, `_make_tenant`, `_make_lease`) e lista de CPFs válidos `:24-39`. Reaproveitar esse estilo para construir leases cobráveis nos testes desta sessão.
- **Model `RentPayment`** (soft-delete + unique ativo): `core/models.py:1237-1272`.
- **Model `MonthSnapshot.is_finalized`** + como a finalização é consultada: `core/models.py:1459,1507` e `core/services/daily_control_service.py:202-209` (`MonthSnapshot.objects.filter(reference_month=..., is_finalized=True)`).

## Escopo

### Arquivos a criar
- `tests/integration/test_rent_calendar_api.py`

### Arquivos a modificar
- `core/views.py` — adicionar **2 actions** ao `DashboardViewSet`:
  - `@action(detail=False, methods=["get"]) rent_calendar` → delega a `RentScheduleService.get_month_schedule(...)`.
  - `@action(detail=False, methods=["post"]) toggle_rent_payment` → delega a `RentScheduleService.toggle_payment(...)`.

> `core/urls.py` **não muda** — o router já expõe as actions do `DashboardViewSet`.

## Especificação

Toda a lógica de negócio vive no `RentScheduleService` (sessão 21). As actions são **finas**: parse/validação de params HTTP, chamada ao service, mapeamento de exceções → status code, `Response`. Direção de dependências: **View → Service → Model** (`.claude/rules/architecture.md`).

### Action `rent_calendar` (GET)

`GET /api/dashboard/rent_calendar/?year=&month=&building_id=`

Comportamento:
1. Ler `year`, `month` dos query params; converter para `int`. Ausência/valor não-inteiro/`month` fora de 1–12 → `400` com `{"error": "<msg PT>"}` (seguir o padrão de validação de `test_daily_control_api.py:121-127`).
2. `building_id` opcional: se presente, converter para `int` (não-inteiro → `400`); se ausente, passar `None` (todos agregados — design D1).
3. Delegar a `RentScheduleService.get_month_schedule(year, month, building_id)`.
4. Retornar `Response(data, status=200)`.

Shape de resposta — **exatamente** o design §4.3 (`year`, `month`, `today`, `next_due_date`, `days[]` com `items[]`, `stats{}`). A view **não monta** esse dict; apenas repassa o retorno do service. O backend **não** retorna `month_label` (derivado no frontend — design §4.1).

### Action `toggle_rent_payment` (POST)

`POST /api/dashboard/toggle_rent_payment/` body `{ "lease_id": <int>, "reference_month": "YYYY-MM-01" }`

Comportamento:
1. Ler `lease_id` (obrigatório; ausente → `400`) e `reference_month` (string `YYYY-MM-DD`; ausente/inválida → `400`). Parsear a data com `date.fromisoformat` (mapear `ValueError` → `400`).
2. `user = cast(User, request.user)` (exemplar: `core/views.py:762`).
3. Delegar a `RentScheduleService.toggle_payment(lease_id, reference_month, user)`.
4. Mapear o resultado do service para status HTTP:
   - Toggle bem-sucedido → `200` com o dict `{status, is_paid, message}` do service.
   - O service sinaliza recusa (mês finalizado, ou pago+dia-passou) → traduzir para `400` com `{"error": "<msg PT>"}`. **Como** o service sinaliza (exceção dedicada vs. retorno) é definido pela sessão 21 — inspecionar `rent_schedule_service.py` e mapear de forma consistente; **não** reimplementar a regra na view.
   - Lease inexistente / não-cobrável → `404`/`400` conforme o service sinalizar.

> Mensagens de erro voltadas ao usuário em **PT**; logs em EN (`.claude/rules/coding-standards.md`). Servidor **sempre revalida** (defesa em profundidade — design §4.4).

### Não remover `mark_rent_paid` nesta sessão

`mark_rent_paid` (`core/views.py:722-775`) permanece **intacto**. O frontend (`late-payments-alert.tsx` / `useMarkRentPaid`) continua consumindo-o até a **sessão 25**, que troca o consumidor para `toggle_rent_payment` e **só então** remove `mark_rent_paid`. Remover agora quebraria o frontend e deixaria a árvore num estado intermediário inválido.

## TDD

Ciclo obrigatório **Red → Green → Refactor → Verify**. Testes primeiro.

### 1. Red — escrever os testes (devem falhar)

Criar `tests/integration/test_rent_calendar_api.py`. Padrão: classes por endpoint, fixtures `model-bakery`, `freezegun` para fixar "hoje", asserts de shape/status. Reaproveitar os helpers de `test_rent_adjustment.py:42-100` (Building/Apartment/Tenant/Lease) e a lista de CPFs válidos `:24-39`. Usar `authenticated_api_client` (admin) e `regular_authenticated_api_client` (não-admin) de `conftest.py`.

Cenários a cobrir (mínimo):

`TestRentCalendarRead` (`GET /api/dashboard/rent_calendar/`):
- `freeze_time` em um dia conhecido (ex.: `2026-06-02`); com leases cobráveis no mês, retorna `200` e o dict tem `year`, `month`, `today`, `next_due_date`, `days` (lista) e `stats` (dict) — shape do design §4.3.
- Cada `day` em `days` tem `day`, `date`, `weekday`, `items`; cada item tem todas as chaves do design §4.3 (`lease_id`, `tenant_name`, `apartment_number`, `building_number`, `rental_value`, `is_paid`, `is_overdue`, `day_passed`, `can_toggle`, `late_fee`, `late_days`).
- `stats` contém `received_total`, `to_receive_total`, `expected_total`, `paid_count`, `due_count`, `overdue_count`, `overdue_total_fee`, `vacant_kitnets_count`, `vacant_kitnets_value`.
- Filtro `building_id`: criar leases cobráveis em 2 prédios; com `building_id=<A>`, os `items` retornados pertencem apenas ao prédio A (e os de B não aparecem).
- `month` fora de 1–12 → `400`; `year`/`month` não-inteiros → `400`; não autenticado (`api_client`) → `401`; autenticado não-admin (`regular_authenticated_api_client`) → `403`.

`TestToggleRentPayment` (`POST /api/dashboard/toggle_rent_payment/`):
- Toggle em lease cobrável sem pagamento e dia **a vencer** → `200`, cria `RentPayment` ativo para `(lease, reference_month)`; segunda chamada → `200`, **soft-delete** do mesmo `RentPayment` (`RentPayment.objects.filter(...)` vazio, `RentPayment.all_objects.filter(...)` mostra `is_deleted=True`). Verificar via ORM real (sem mock).
- Recusa desmarcar quando **pago + dia já passou**: com `freeze_time` após o vencimento e um `RentPayment` existente → `400` (não apaga o pagamento).
- Mês **finalizado** bloqueia: criar `MonthSnapshot(reference_month=<mês>, is_finalized=True)` e tentar toggle nesse mês → `400` (nenhuma alteração em `RentPayment`).
- `lease_id` ausente → `400`; `reference_month` ausente/inválido (ex.: `"2026-13-01"`) → `400`.
- Não autenticado → `401`; não-admin → `403`.

**Mock policy** (`.claude/rules/testing.md`): mockar **apenas** boundaries externos. Tempo via `freezegun`. **NUNCA** mockar `RentScheduleService`, ORM, serializers, ou DRF — exercitar o caminho real View → Service → Model com banco de teste (`--reuse-db`). `model-bakery` para dados; nada de criação manual com ORM cru fora dos helpers.

Rodar (devem falhar — actions ainda não existem):
```bash
python -m pytest tests/integration/test_rent_calendar_api.py -q
```

### 2. Green — implementar o mínimo

Adicionar as 2 actions ao `DashboardViewSet` (`core/views.py`), próximas a `late_payment_summary`/`mark_rent_paid`, seguindo o estilo de `:644-775`. Manter `permission_classes = [IsAdminUser]` no nível do ViewSet (`:598`) — não duplicar permissão por action.

Reaproveitar imports já presentes em `core/views.py:1-37` (`status`, `action`, `Request`, `Response`, `cast`, `User`, `date`). Importar `RentScheduleService` de `core/services/rent_schedule_service.py` (import direto da fonte — **sem** re-export/barrel; `.claude/rules/coding-standards.md`). Se a sessão 21 adicionou o service ao `core/services/__init__.py:__all__`, importar de lá; caso contrário, importar do módulo. **Não** adicionar re-exports novos.

Rodar até passar:
```bash
python -m pytest tests/integration/test_rent_calendar_api.py -q
```

### 3. Refactor

Limpar sem mudar comportamento. Extrair o parse de `year`/`month`/`building_id` para um helper privado **somente se** houver duplicação real com outra action (DRY — não especular, YAGNI). Docstrings só onde a lógica não é óbvia (`.claude/rules/coding-standards.md`). Confirmar que as actions ficaram finas (sem lógica de negócio). Nenhum `# noqa`/`# type: ignore`.

### 4. Verify

```bash
python -m pytest tests/integration/test_rent_calendar_api.py -q
ruff check core/views.py tests/integration/test_rent_calendar_api.py
ruff format --check core/views.py tests/integration/test_rent_calendar_api.py
mypy core/views.py
pyright core/views.py
```

> Memória de testes do projeto: rodar **apenas os arquivos editados** desta sessão. A suíte completa tem problemas pré-existentes de xdist/Redis e não deve ser usada como gate aqui. Rodar também o teste de regressão do `DailyControlService` se quiser confirmar não-regressão da sessão 21: `python -m pytest tests/unit/test_financial/test_daily_control_service.py tests/integration/test_daily_control_api.py -q` (não obrigatório nesta sessão; foi gate da 21).

## Constraints — NÃO fazer

- **NÃO** remover, renomear ou alterar `mark_rent_paid` (`core/views.py:722-775`) — isso é da **sessão 25**.
- **NÃO** alterar `RentScheduleService` nem `DailyControlService` — esta sessão **apenas consome** o service produzido na 21. Se faltar algo na API do service, parar e registrar no SESSION_STATE, não improvisar lógica na view.
- **NÃO** colocar lógica de negócio na view (clamping, regra de toggle, cálculo de stats/multa, query de leases cobráveis) — tudo isso vive no service.
- **NÃO** tocar em `core/urls.py` (router já expõe as actions).
- **NÃO** fazer frontend (hooks, componentes, `use-dashboard.ts`, `late-payments-alert.tsx`) — sessões 23/24/25.
- **NÃO** adicionar cache ao endpoint (design §4.3: não cacheado — YAGNI).
- **NÃO** criar serializer novo para a resposta — os endpoints do dashboard retornam `dict` direto (exemplar `:620,:695`).
- **NÃO** usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`. **NÃO** criar re-exports/barrels nem shims de retrocompatibilidade. SOLID/DRY/KISS/YAGNI.
- **NÃO** mockar `RentScheduleService`, ORM, serializers ou DRF nos testes.

## Critérios de Aceite

- [ ] `tests/integration/test_rent_calendar_api.py` criado, exercitando View → Service → Model com banco real (sem mock de internals).
- [ ] `DashboardViewSet` tem `rent_calendar` (GET) delegando a `RentScheduleService.get_month_schedule`.
- [ ] `DashboardViewSet` tem `toggle_rent_payment` (POST) delegando a `RentScheduleService.toggle_payment`.
- [ ] `mark_rent_paid` permanece inalterado em `core/views.py`.
- [ ] `permission_classes = [IsAdminUser]` mantido; não-admin → `403`, não autenticado → `401` em ambas as actions.
- [ ] `GET rent_calendar` retorna shape do design §4.3 (`year`/`month`/`today`/`next_due_date`/`days[]` com `items[]`/`stats{}`) sob `freeze_time`.
- [ ] Filtro `building_id` restringe os itens ao prédio informado.
- [ ] `POST toggle` cria `RentPayment` na 1ª chamada e faz soft-delete na 2ª (verificado via `objects`/`all_objects`).
- [ ] `POST toggle` recusa (`400`) desmarcar quando pago + dia já passou.
- [ ] `POST toggle` bloqueia (`400`) mês finalizado (`MonthSnapshot.is_finalized=True`).
- [ ] Params inválidos (`year`/`month`/`building_id` não-inteiros, `month` fora de 1–12, `lease_id` ausente, `reference_month` inválido) → `400`.
- [ ] `python -m pytest tests/integration/test_rent_calendar_api.py -q` 100% verde.
- [ ] `ruff check`/`ruff format --check`/`mypy`/`pyright` limpos nos arquivos tocados (zero warnings).
- [ ] `core/urls.py` inalterado; nenhum re-export/barrel criado; nenhuma alteração em `RentScheduleService`/`DailyControlService`.

## Handoff

1. Rodar e confirmar verde: `python -m pytest tests/integration/test_rent_calendar_api.py -q` + lint/type nos arquivos tocados (comandos da seção Verify).
2. Atualizar `prompts/SESSION_STATE.md`: marcar sessão 22 concluída; registrar que `rent_calendar`/`toggle_rent_payment` estão expostos, que `mark_rent_paid` **ainda existe** (remoção pendente na sessão 25), e o exato mecanismo de sinalização de erro do service consumido (exceção vs. retorno) para a próxima sessão.
3. Commitar (branch a partir de `master` se ainda na default):
   ```
   feat(backend): add rent_calendar and toggle_rent_payment dashboard endpoints

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. Próxima sessão: `prompts/23-*.md` (frontend data layer) — começa lendo o SESSION_STATE.md.
