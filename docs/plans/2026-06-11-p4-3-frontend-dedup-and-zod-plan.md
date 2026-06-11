# Plano P4.3 — Frontend: dedup de modais + criação atômica de lease + gotcha Zod + dead code

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P4 · **Branch sugerida:** `refactor/frontend-quality` · **Depende de:** nenhum

## Objetivo

Eliminar a duplicação de ~1.600 LOC entre `lease-form-modal.tsx` e `tenant-lease-modal.tsx` extraindo um único `LeaseFormModal` parametrizado, e tornar a criação de locação atômica via um endpoint/serializer de backend (lease + dependente residente + `due_day` em uma transação), substituindo a orquestração de 3+ requests não-atômica que hoje persiste PATCHes parciais quando a criação da lease falha. Em paralelo, corrige bugs de contrato FE↔API do módulo NOVO (criação de Funcionário e Plano de Parcelas quebrada por `condominium_id` obrigatório), o gotcha do dual pattern no `expenseSchema` (superRefine exige `_id` write-only no parse de leitura e derruba a lista), a invalidação incompleta de caches financeiros após pagar/gerar contas, e remove dead code / `eslint-disable` / regras de dinheiro duplicadas no frontend. Importa porque os dois primeiros itens afetam integridade de dados (estado parcial em fluxo de cobrança) e funcionalidade ativa (dois fluxos de criação do módulo novo 100% quebrados pela UI).

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | `lease-form-modal` e `tenant-lease-modal` ~1.600 LOC quase duplicadas, já divergiram em campos financeiros | `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx:1-917` · `frontend/app/(dashboard)/tenants/_components/tenant-lease-modal.tsx:1-702` | Extrair `LeaseFormModal` único parametrizado (1 schema, 1 mutation hook), deletar a cópia |
| ALTO | Orquestração de 3+ requests SEM atomicidade (PATCH persiste, lease falha → estado parcial) | `lease-form-modal.tsx:255-348` · `tenant-lease-modal.tsx:243-292` | Endpoint/serializer backend atômico (lease + dependente + `due_day` em `transaction.atomic`) + 1 mutation hook |
| ALTO | Componentes chamam `apiClient` direto (modais, global-search, main-layout) | `lease-form-modal.tsx:57,273,326` · `tenant-lease-modal.tsx:55` · `global-search.tsx:15,60-64` · `main-layout.tsx:9,27` | Mover toda chamada para hooks TanStack Query; main-layout usa `useCurrentUser` |
| ALTO | Busca global navega para `/dashboard/*` inexistente → 404 em todo clique | `frontend/components/search/global-search.tsx:78,92,106,120,134` | Trocar URLs hardcoded por `ROUTES.*` reais |
| ALTO→MÉDIO | Criar Funcionário e Plano de Parcelas quebrados — form não envia `condominium_id` obrigatório (serializer não defaulta) | `finances/serializers.py:475-477,548-550` | Aplicar `_apply_default_condominium` no `validate()` + `required=False` em `condominium_id` |
| ALTO→MÉDIO | Gotcha dual pattern: `expenseSchema.superRefine` exige `_id` write-only no parse de LEITURA e derruba a lista | `frontend/lib/schemas/expense.schema.ts:78-106` | Separar read schema (sem `validateExpenseRules`) do form schema; varrer todos os schemas com refine/superRefine |
| ALTO→MÉDIO | Mutations de Bill/Payment não invalidam dashboards/reservas | `frontend/lib/api/hooks/use-bills.ts:118-122,285` · `use-payments.ts:47-52` | Estender `invalidateBillCaches`/`invalidatePaymentCaches` para overview/monthlyBalance/byCategory/projection/ownerDistribution/reserves |
| MÉDIO | Regras de dinheiro duplicadas no frontend (tag fee hardcoded no payload + cálculos de multa mortos) | `frontend/lib/utils/helpers.ts:1-48` · `constants.ts:40-46` | Backend calcula default de `tag_fee` (serializer); frontend só exibe; deletar funções/constantes mortas |
| MÉDIO | Fail-fast `.map(schema.parse)` derruba a página inteira (~30 hooks) | `use-bills.ts:101` (+ ~30 hooks de lista) | Helper `parseList(schema, items)` com `safeParse` + telemetria por item |
| MÉDIO | `eslint-disable` no client.ts (regra CRITICAL) + unwrap de paginação duplicado | `frontend/lib/api/client.ts:22-36` | Remover unwrap do interceptor (e os 3 `eslint-disable`); `extractResults` nos hooks é a única fonte |
| MÉDIO | Código morto / órfãos: `use-payments`, `useCurrentUser`, `/admin/users` sem link, Bell inerte, re-export em `use-bills` | `use-payments.ts` · `use-auth.ts:107` · `header.tsx` · `use-bills.ts:305` | `useCurrentUser` no main-layout; remover Bell/comentário; `/admin/users` no menu; remover re-export |
| MÉDIO | `due_date` UTC rollover no legado (`new Date(ISO)` + `setMonth` + `toISOString`) | `frontend/app/(dashboard)/financial/expenses/details/_components/expense-edit-modal.tsx:249-296` | Aritmética split-based com clamp do dia ao último dia do mês alvo |
| MÉDIO→BAIXO | `payment_date` default UTC nos modais legados grava no dia seguinte após 21h BRT | `financial/_components/quick-payment-modal.tsx:54` · `person-payment-form-modal.tsx:60` · `person-income-form-modal.tsx:65` | Helper `todayISO()` local (getFullYear/Month/Date) único em `lib/utils` |

## Abordagem técnica

Ordem de execução (cada passo é verificável e independente; passos de backend antes do FE que depende deles).

### 1. Backend — default de `condominium_id` em Employee e InstallmentPlan (bug do app NOVO, prioridade)

Em `finances/serializers.py`:
- `InstallmentPlanSerializer` (linhas 473-543): mudar `condominium_id` (linha 475-477) para `required=False`; o `validate()` existente (linha 530) já roda — acrescentar `_apply_default_condominium(self.instance, attrs)` como primeira linha (mesmo padrão de `CategorySerializer.validate` linha 122, `BillSerializer.validate` linha 356, `ReserveSerializer.validate` linha 625, `IncomeEntrySerializer.validate` linha 713).
- `EmployeeSerializer` (linhas 546-588): mudar `condominium_id` (linha 548-550) para `required=False`; a classe NÃO tem `validate()` hoje — adicionar `def validate(self, attrs: dict[str, object]) -> dict[str, object]:` que chama `_apply_default_condominium(self.instance, attrs)` e retorna `attrs`.

`_apply_default_condominium` (linhas 49-60) já levanta `ValidationError({"condominium_id": Condominium.NOT_CONFIGURED_MESSAGE})` quando não há singleton — comportamento correto preservado. NÃO mexer no frontend dos dois modais: `employee-form-modal.tsx:103-113` e `installment-plan-form-modal.tsx` já omitem `condominium_id` exatamente como `income-entry-form-modal` (padrão correto); o bug é só a ausência do default no serializer.

### 2. Backend — endpoint atômico de criação de lease

Hoje a criação de lease envolve, no componente: (a) opcional PATCH `/tenants/{id}/` reenviando toda a lista de `dependents` para criar o residente, (b) re-identificar o dependente por `name`+`cpf_cnpj` no response, (c) PATCH `/tenants/{id}/` para `due_day`, (d) POST `/leases/`. Se (d) falha, (a)-(c) já persistiram.

Criar um único caminho transacional no backend:
- Novo service `core/services/lease_creation_service.py` com função stateless `create_lease_with_resident(*, validated_lease_data, due_day, new_dependent, user) -> Lease`, executando tudo em `transaction.atomic()`:
  1. Se `new_dependent` for informado (name+phone), cria `Dependent` via instância + `full_clean()` + `save(update fields com updated_by)` vinculado ao `responsible_tenant`, e usa seu `pk` como `resident_dependent`. (Resolve a re-identificação frágil por name/cpf.)
  2. Atualiza `responsible_tenant.due_day` quando difere do atual (`tenant.due_day = due_day`, `tenant.save(update_fields=["due_day", "updated_at", "updated_by"])`).
  3. Cria a `Lease` reusando a lógica de derivação já existente em `LeaseSerializer.create` (derivar `rental_value` por `number_of_tenants`, default de `last_rent_increase_date`, `tenants.set`, sync de `apartment.last_rent_increase_date`). Para não duplicar (DRY), extrair a derivação de `LeaseSerializer.create` (serializers.py:501-530) para o service e o serializer passa a delegar a ela.
- Nova `@action(detail=False, methods=["post"], url_path="create_with_resident", permission_classes=[IsAdminUser])` em `LeaseViewSet` (core/views.py:254): valida o payload com um `LeaseCreateAtomicSerializer` (campos da lease + `due_day` + `new_dependent` opcional `{name, phone, cpf_cnpj}`), chama o service, retorna `LeaseSerializer(lease).data` com 201. Mensagens de erro em PT (usuário), logs em EN.

Contrato FE↔API (dois lados):
- FE envia em UMA request: todos os campos hoje em `payload` (lease-form-modal.tsx:305-320) + `due_day` + `new_dependent` (ou `null`). Sem PATCH prévio de tenant nem POST separado.
- Backend devolve a `Lease` criada (shape do `LeaseSerializer`, já consumido pelo `leaseSchema`).

### 3. FE — `LeaseFormModal` único parametrizado + mutation hook único

- Criar `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` como o componente único parametrizado por prop `mode: 'standalone' | 'from-tenant' | 'transfer'`:
  - `from-tenant`: pré-seleciona `responsible_tenant` a partir de `tenant` (não exibe o select de inquilino), substitui o atual `tenant-lease-modal` no fluxo de criação.
  - `transfer`: mantém o caminho `useTransferLease` (POST `/leases/{id}/transfer/`) — esse fluxo já é atômico no backend e NÃO passa pelo novo endpoint.
  - `standalone`: fluxo atual de `lease-form-modal` (edição + criação a partir da página de Locações).
- Um único `leaseFormSchema` Zod (já existe o superset em lease-form-modal.tsx:72-90 com `due_day`, `prepaid_until`, `is_salary_offset`, `last_rent_increase_date`, `responsible_tenant_id`). O fluxo `from-tenant` mantém esses campos especiais que hoje SÓ existem em `lease-form-modal` — eliminando a divergência (o `tenant-lease-modal` não tinha `due_day`/`is_salary_offset`).
- Substituir `createDependentAndGetId` (lease-form-modal.tsx:255-288 e a cópia idêntica tenant-lease-modal.tsx:~210-241) e os PATCHes inline pelo novo hook `useCreateLeaseWithResident` (mutationFn → POST `/leases/create_with_resident/`), que recebe `new_dependent` no payload em vez de criar o dependente client-side.
- Atualizar os call sites: a página de Locações usa `<LeaseFormModal mode="standalone" />`; a página/ações de Inquilinos usam `<LeaseFormModal mode="from-tenant" tenant={...} />` para criar e `mode="transfer"` para trocar de kitnet.
- Deletar `frontend/app/(dashboard)/tenants/_components/tenant-lease-modal.tsx`.
- Parse de data local: reusar `parseLocalDate` (split-based, já presente em ambos) e `format(date, 'yyyy-MM-dd')` no submit — sem `new Date(ISO)`/`toISOString`.

### 4. FE — `useCreateLeaseWithResident` hook

- Em `frontend/lib/api/hooks/use-leases.ts`: adicionar `useCreateLeaseWithResident()` (mutationFn POST `/leases/create_with_resident/`, parse com `leaseSchema`), invalidando `queryKeys.leases.all`, `queryKeys.apartments.all`, `queryKeys.tenants.all` (due_day muda o tenant), `queryKeys.dashboard.all`. `useCreateLease` (linha 54) permanece para edições/outros usos; `useTransferLease` (linha 262) inalterado.

### 5. FE — `tag_fee` calculado no backend

- Remover `calculateTagFee` (helpers.ts:6-8) e `TAG_FEES` (constants.ts:40-43) do payload de criação. O backend já parametriza via `settings.DEFAULT_TAG_FEE_SINGLE/MULTIPLE` (FeeCalculatorService.calculate_tag_fee). O serializer atômico (passo 2) deve aplicar o default de `tag_fee` a partir de `number_of_tenants` quando o campo não vier (ou vier `null`), de forma que o frontend apenas EXIBA o valor (campo continua editável para override manual no form, mas o default exibido vem do backend via `useTagFeeDefault`/incluído no fluxo, sem hardcode no FE). Para o display no form (antes do submit), expor o cálculo do backend — opção mínima e KISS: o componente envia `tag_fee` somente quando o usuário editou manualmente; caso contrário omite e o backend preenche. O resumo no form mostra "R$ 20,00 / R$ 40,00" como texto estático informativo (já existe na linha 681), sem reimplementar a regra.

### 6. FE — separar read schema do form schema no `expenseSchema` (+ sweep)

- `frontend/lib/schemas/expense.schema.ts`: hoje `expenseSchema = expenseBaseSchema.superRefine(validateExpenseRules)` (linha 106) e `useExpenses/useExpense` fazem `.map((e) => expenseSchema.parse(e))` no READ. `validateExpenseRules` exige `person_id`/`credit_card_id`/`building_id` que são write-only no `ExpenseSerializer` → ausentes no read → ZodError derruba a lista.
  - Exportar `expenseReadSchema = expenseBaseSchema` (SEM `superRefine`) e usar nos hooks de leitura.
  - Manter `expenseSchema = expenseBaseSchema.superRefine(validateExpenseRules)` SOMENTE para validação de FORMULÁRIO (resolver do react-hook-form), onde os `_id` estão presentes.
  - Corrigir `validateExpenseRules`: a linha 93 usa `isPersonFieldVisible(type)` (inclui PERSON_OPTIONAL_TYPES); trocar por `PERSON_REQUIRED_TYPES` para não exigir pessoa em `fixed_expense`/`one_time_expense`.
- Sweep de todos os schemas com refine/superRefine (resultado da varredura já feita):
  - `expense.schema.ts:106` — VULNERÁVEL (exige `_id` write-only no read) → corrigir conforme acima.
  - `installment-plan.schema.ts:45` — JÁ CORRETO (aceita objeto aninhado OU `_id`); usar como referência.
  - `employee.schema.ts:37` — SAFE (valida `base_salary`, campo read+write presente no read).
  - `apartment.schema.ts:22`, `rent-adjustment.schema.ts:34`, `settings.ts:16` — SAFE (validam escalares presentes no read / form-only). Nenhuma alteração; documentar no PR que foram revisados.

### 7. FE — invalidação completa de caches financeiros

- `frontend/lib/api/hooks/use-bills.ts` `invalidateBillCaches` (linha 118-122): acrescentar invalidação de `queryKeys.finances.overview.all`, `queryKeys.finances.monthlyBalance.all`, `queryKeys.finances.byCategory.all`, `queryKeys.finances.projection.all`, `queryKeys.finances.ownerDistribution.all` (todas as chaves existem em query-keys.ts:227-252).
- `frontend/lib/api/hooks/use-payments.ts` `invalidatePaymentCaches` (linha 47-52): mesma extensão; em `usePayBill` (use-bills.ts:245), quando `funded_from === 'reserve'`, invalidar também `queryKeys.finances.reserves.all` e `queryKeys.finances.reserveMovements.all`.
- DRY: extrair um helper compartilhado `invalidateFinanceMoneyCaches(queryClient)` em um módulo de hooks de finances (ex.: `use-bills.ts` exportando a função, ou um `finances/cache-invalidation.ts` interno de hooks) e usá-lo nos dois pontos.

### 8. FE — helper `parseList` com `safeParse` + telemetria

- Criar `frontend/lib/api/parse-list.ts` com `parseList<T>(schema, items): T[]` que faz `schema.safeParse` por item, em falha `console.error` (e captura por linha — Sentry se configurado), e RETORNA apenas os itens válidos (degradação graciosa) — política consciente única do projeto.
- Substituir `extractResults(data).map((x) => schema.parse(x))` por `parseList(schema, extractResults(data))` em todos os hooks de lista (~30 ocorrências: use-bills, use-installment-plans, use-employees, use-income-entries, use-reserves, use-payments, use-leases, use-tenants, use-expenses, use-apartments, use-buildings, etc.). Refatoração completa (todos os consumidores), sem deixar `.map(parse)` remanescente em hooks de lista.

### 9. FE — remover `eslint-disable` + unwrap duplicado no client

- `frontend/lib/api/client.ts:19-38`: remover o bloco de unwrap de paginação (`response.data = data.results`) e os 3 `eslint-disable`. Os hooks já tratam o envelope via `extractResults`/`PaginatedResponse<T> | T[]`. Verificar os poucos hooks tipados apenas como `T[]` (ex.: `useBuildings`, `useFurniture`) e tipá-los como `PaginatedResponse<T> | T[]` + `extractResults`, pois deixarão de receber o array já desembrulhado.

### 10. FE — `global-search` para ROUTES reais + hooks

- `frontend/components/search/global-search.tsx`: trocar `url: '/dashboard/buildings'` → `ROUTES.BUILDINGS`, `/dashboard/apartments` → `ROUTES.APARTMENTS`, `/dashboard/tenants` → `ROUTES.TENANTS`, `/dashboard/leases` → `ROUTES.LEASES`, `/dashboard/furniture` → `ROUTES.FURNITURE` (linhas 78, 92, 106, 120, 134; ROUTES em constants.ts:48-81).
- Substituir os 5 `apiClient.get` em `Promise.all` (linhas 59-65) e o estado em `useState` por `useQuery` por recurso (com `enabled` no termo e o debounce já existente), eliminando os casts `as Building[]`. Os hooks de lista já existem (`useBuildings`, `useApartments`, `useTenants`, `useLeases`, `useFurniture`) e aceitam filtro `search` via params — usar uma variante com `{ search: term }` ou query dedicada de busca.

### 11. FE — main-layout usa `useCurrentUser`

- `frontend/components/layouts/main-layout.tsx:24-30`: remover o `apiClient.get('/auth/me/')` manual e usar o hook `useCurrentUser` (use-auth.ts:107) — deixa de duplicar a chamada e remove o import direto de `apiClient`. Setar `user` no store via efeito sobre o `data` do hook (ou já consumir do hook onde for usado).

### 12. FE — dead code

- Header (`frontend/components/layouts/header.tsx`): remover o bloco comentado "Uncomment when implementing notifications" e o botão `Bell` inerte (sem ação).
- `use-bills.ts:305`: remover `export type { Bill, BillLineItem };` (re-export). Atualizar consumidores para importar de `@/lib/schemas/finances/bill.schema` (a maioria já importa de lá).
- `/admin/users`: adicionar entrada no menu/sidebar condicionada a `user?.is_staff` (rota existe mas é inacessível pela navegação).
- `use-payments.ts`: este hook passa a ter consumidores reais (`invalidatePaymentCaches` é usado por mutations de payment do módulo novo). NÃO deletar — apenas estender a invalidação (passo 7). Confirmar com grep antes de qualquer remoção.

### 13. FE — aritmética de data split-based no legado

- `expense-edit-modal.tsx:249-296`: substituir `new Date(ISO)` + `dueDate.setMonth(...)` + `toISOString()` por cálculo puro: split do `YYYY-MM-DD`, somar meses em ano/mês inteiros e clampar o dia ao último dia do mês alvo (`min(day, lastDayOf(targetMonth))`), formatando de volta como `YYYY-MM-DD` por string (sem objeto Date). Referência: helpers split-based já existentes no módulo novo (`convert-deferred-dialog.tsx`, `installment-schedule-field.tsx`).
- `quick-payment-modal.tsx:54`, `person-payment-form-modal.tsx:60`, `person-income-form-modal.tsx:65`: trocar `new Date().toISOString().split('T')[0]` por um `todayISO()` local (extraído de `bill-payment-dialog.tsx:41-46`, getFullYear/getMonth/getDate locais) colocado em `lib/utils` como fonte única. Remover/ reimplementar `formatDateISO` morto (formatters.ts:98-102) em horário local.

## Arquivos a criar / modificar

Backend:
- `finances/serializers.py` — `required=False` + `_apply_default_condominium` em `InstallmentPlanSerializer.validate` (acrescentar linha) e novo `EmployeeSerializer.validate`.
- `core/services/lease_creation_service.py` (novo) — `create_lease_with_resident(...)` transacional; extrair derivação de `LeaseSerializer.create`.
- `core/serializers.py` — `LeaseCreateAtomicSerializer` (novo, no mesmo arquivo) + `LeaseSerializer.create` delega a derivação ao service (DRY); default de `tag_fee` por `number_of_tenants`.
- `core/views.py` — `@action create_with_resident` em `LeaseViewSet`.
- `tests/integration/test_lease_atomic_create.py` (novo), `tests/integration/test_finances_employee_installment_create.py` (novo ou estender existente).

Frontend:
- `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` — reescrito como componente único parametrizado (`mode`).
- `frontend/app/(dashboard)/tenants/_components/tenant-lease-modal.tsx` — DELETADO; call sites atualizados para `LeaseFormModal mode="from-tenant"|"transfer"`.
- `frontend/lib/api/hooks/use-leases.ts` — `useCreateLeaseWithResident`; `useTransferLease` inalterado.
- `frontend/lib/api/hooks/use-bills.ts` + `use-payments.ts` — invalidação estendida (helper compartilhado); remover re-export em use-bills.ts:305.
- `frontend/lib/api/parse-list.ts` (novo) — `parseList` com safeParse + telemetria; aplicado em ~30 hooks de lista.
- `frontend/lib/api/client.ts` — remover unwrap + `eslint-disable`.
- `frontend/lib/schemas/expense.schema.ts` — `expenseReadSchema` + `validateExpenseRules` com `PERSON_REQUIRED_TYPES`.
- `frontend/lib/api/hooks/use-expenses.ts` — usar `expenseReadSchema` no read.
- `frontend/components/search/global-search.tsx` — ROUTES + useQuery.
- `frontend/components/layouts/main-layout.tsx` — `useCurrentUser`.
- `frontend/components/layouts/header.tsx` — remover Bell/comentário.
- `frontend/components/layouts/sidebar.tsx` (ou menu) — entrada `/admin/users` gated por is_staff.
- `frontend/lib/utils/helpers.ts` + `constants.ts` — remover `calculateTagFee`/`calculateLateFee`/`calculateDueDateChangeFee`/`calculateDaysLate`/`calculateFinalDate` mortas + `TAG_FEES`/`LATE_FEE_RATE`/`DAYS_PER_MONTH`.
- `frontend/lib/utils/__tests__/helpers.test.ts` — remover/atualizar testes das funções deletadas.
- `frontend/lib/utils/date.ts` (ou formatters.ts) — `todayISO()` local único; `formatDateISO` corrigido/removido.
- `frontend/app/(dashboard)/financial/expenses/details/_components/expense-edit-modal.tsx`, `quick-payment-modal.tsx`, `person-payment-form-modal.tsx`, `person-income-form-modal.tsx` — datas split-based / `todayISO`.
- Testes FE: `lease-form-modal.test.tsx` (atomicidade + modos), `global-search.test.tsx` (navegação), `parse-list.test.ts`, `expense.schema.test.ts` (read shape), `use-bills.test.ts`/`use-payments.test.ts` (invalidação), MSW data realista para expenses/employees/installment-plans.

## TDD — cenários de teste

Backend (pytest, mock só na fronteira: nenhuma fronteira externa aqui — usar DB real):
- `test_create_lease_with_resident_atomic_rolls_back_on_lease_error` — força erro na criação da lease (ex.: apartamento já alugado / constraint) e assertar que o `Dependent` e o `due_day` do tenant NÃO foram persistidos (prova o bug do estado parcial).
- `test_create_lease_with_resident_creates_dependent_and_links_resident` — `new_dependent` informado → `resident_dependent` aponta para o dependente recém-criado (sem re-identificação por name/cpf).
- `test_create_lease_with_resident_updates_tenant_due_day` — `due_day` diferente do atual atualiza o tenant; igual → no-op.
- `test_create_lease_with_resident_derives_rental_and_tag_fee` — `rental_value`/`tag_fee` omitidos derivam de `number_of_tenants` (1→single, 2→double/MULTIPLE).
- `test_create_lease_with_resident_requires_admin` — não-staff recebe 403.
- `test_installment_plan_create_defaults_condominium` — POST sem `condominium_id` → 201, condomínio = singleton (regressão do bug ALTO→MÉDIO).
- `test_employee_create_defaults_condominium` — idem para Employee.
- `test_installment_plan_create_without_singleton_returns_400` — sem `Condominium.get_default()` → 400 PT `NOT_CONFIGURED_MESSAGE`.

Frontend (Vitest + MSW na fronteira HTTP; SEM mock de hooks internos):
- `lease-form-modal · cria lease em uma única request` — render `mode="from-tenant"`, preencher, submit → MSW recebe 1 POST `/leases/create_with_resident/` e nenhum PATCH `/tenants/` (regressão da não-atomicidade).
- `lease-form-modal · modo standalone edita lease` — PUT `/leases/{id}/`.
- `lease-form-modal · modo transfer usa endpoint de transfer` — POST `/leases/{id}/transfer/`.
- `lease-form-modal · campos especiais presentes no fluxo from-tenant` — `due_day`/`is_salary_offset`/`prepaid_until` aparecem (prova fim da divergência).
- `global-search · clicar resultado navega para rota real` — clicar prédio → `router.push(ROUTES.BUILDINGS)` (regressão do 404).
- `parseList · item inválido não derruba a lista` — lista com 1 item fora do contrato → retorna os válidos + `console.error` chamado (regressão "Parcelas vazias"/expenses).
- `expense read schema · parse de payload real (sem person_id/credit_card_id) não lança` — payload bruto da API com `card_purchase` sem `_id` → `expenseReadSchema.parse` OK (regressão do gotcha).
- `useExpenses · lista de despesas card_purchase carrega` — MSW retorna shape real → hook resolve com itens (não vazio).
- `invalidateBillCaches · invalida dashboards` — após `useCreateBillWithLines`/`usePayBill`, `overview`/`monthlyBalance`/`byCategory`/`projection`/`ownerDistribution` invalidados.
- `usePayBill funded_from=reserve · invalida reservas` — `reserves`/`reserveMovements` invalidados só quando reserve.
- `employee create · payload sem condominium_id` — MSW assert que o body NÃO tem `condominium_id` e o create resolve 201 (espelha income-entry).
- `installment-plan create · payload sem condominium_id` — idem.
- `client · resposta paginada chega aos hooks como envelope` — sem unwrap no interceptor, `extractResults` desembrulha; `count` acessível.
- `expense-edit-modal · due_date de 31/01 +1 mês = 28/02` (não bissexto) e `29/02` (bissexto) — sem rollover; `quick-payment-modal · payment_date usa data local` (freeze 23:30 BRT → dia correto).

## Migrations / dados

N/A — nenhum modelo novo, nenhuma coluna alterada. O endpoint atômico e os defaults de `condominium_id` operam sobre tabelas existentes; não há tabela nova (logo, nada de RLS). Sem correção de dado vivo neste plano (os defaults de `condominium_id` corrigem fluxo de criação, não dados já gravados). Sem backup necessário.

## Constraints (o que NÃO fazer)

- NÃO refatorar profundamente o módulo legado `financial/` além das correções pontuais de data citadas (expense-edit-modal, quick-payment/person-payment/person-income modais): são correções de dinheiro/data que rodam em prod, não reescrita.
- NÃO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore` em nenhum ponto — o objetivo do passo 9 é justamente remover os existentes.
- NÃO introduzir backwards-compat shims nem re-exports — `tenant-lease-modal.tsx` é DELETADO (sem wrapper), todos os call sites migram para `LeaseFormModal`.
- NÃO mockar hooks internos nos testes FE — usar MSW na fronteira HTTP (a política de mocks é o motivo de dois bugs terem passado).
- NÃO mexer no `useTransferLease` / endpoint `/leases/{id}/transfer/` (já é atômico) — só o fluxo de CRIAÇÃO usa o endpoint novo.
- NÃO reintroduzir cálculo de regra de dinheiro no frontend (tag fee, multa) — backend é a fonte; o frontend só exibe.
- NÃO tratar o RLS-sem-policy, `page_size` grande, ou a existência do módulo legado como bugs (falsos positivos conhecidos).
- NÃO deletar `use-payments.ts` — ele tem consumidores após o passo 7 (confirmar por grep).

## Critérios de aceite (binários)

- [ ] POST `/leases/create_with_resident/` cria lease + dependente residente + atualiza `due_day` em UMA transação; falha na lease NÃO deixa dependente/`due_day` persistidos.
- [ ] Não existe mais PATCH `/tenants/{id}/` no caminho de CRIAÇÃO de lease (verificável por teste MSW).
- [ ] `tenant-lease-modal.tsx` foi deletado; `LeaseFormModal` único cobre `standalone`/`from-tenant`/`transfer` e expõe `due_day`/`is_salary_offset`/`prepaid_until` no fluxo from-tenant.
- [ ] POST `/finances/employees/` e `/finances/installment-plans/` sem `condominium_id` retornam 201 (não 400).
- [ ] `expenseReadSchema.parse` de um payload real de `card_purchase` (sem `person_id`/`credit_card_id`/`building_id`) NÃO lança; lista de despesas carrega.
- [ ] `invalidateBillCaches`/`invalidatePaymentCaches` invalidam overview/monthlyBalance/byCategory/projection/ownerDistribution; `usePayBill` com `funded_from='reserve'` invalida reservas.
- [ ] `parseList` retorna itens válidos e loga inválidos; nenhum hook de lista usa `.map(schema.parse)` direto.
- [ ] `frontend/lib/api/client.ts` não contém nenhum `eslint-disable`; envelope paginado é tratado só pelos hooks.
- [ ] Todo resultado da busca global navega para uma rota existente (sem `/dashboard/*`).
- [ ] `helpers.ts` não contém `calculateTagFee`/`calculateLateFee`/`calculateDueDateChangeFee`/`calculateDaysLate`/`calculateFinalDate`; `constants.ts` não contém `TAG_FEES`/`LATE_FEE_RATE`/`DAYS_PER_MONTH`; nenhum import quebrado.
- [ ] main-layout usa `useCurrentUser` (sem `apiClient` direto); Bell/comentário removidos do Header; `/admin/users` acessível por menu gated por is_staff; re-export em use-bills.ts removido.
- [ ] Datas de vencimento/pagamento nos modais legados citados são split-based/local (31/01+1mês=28/02; 23:30 BRT → dia correto).
- [ ] Gate de verificação (abaixo) passa com zero erros e zero warnings nos arquivos editados + regressão dirigida.

## Gate de verificação

Backend (escopado nos arquivos editados + regressão dirigida; suite cheia tem flakiness pré-existente de xdist/Redis — não bloqueia):
```
ruff check finances/serializers.py core/services/lease_creation_service.py core/serializers.py core/views.py
ruff format --check finances/serializers.py core/services/lease_creation_service.py core/serializers.py core/views.py
mypy core/ && pyright
python -m pytest tests/integration/test_lease_atomic_create.py tests/integration/test_finances_employee_installment_create.py -p no:xdist
```

Frontend:
```
cd frontend && npm run lint && npm run type-check
npm run test:unit -- lease-form-modal global-search parse-list expense.schema use-bills use-payments use-expenses use-leases
```

Zero erros E zero warnings (Ruff, mypy, Pyright, ESLint, TypeScript, pytest/vitest).

## Handoff

Commit sugerido:
```
refactor(frontend): unify LeaseFormModal + atomic lease create, fix condominium_id default, expense read schema, finance cache invalidation

- Extract single parameterized LeaseFormModal (standalone/from-tenant/transfer); delete tenant-lease-modal duplicate (~1.6k LOC)
- Add atomic POST /leases/create_with_resident/ (lease + resident dependent + due_day in one transaction) + useCreateLeaseWithResident
- Default condominium_id on Employee/InstallmentPlan serializers (_apply_default_condominium) — fixes broken create in finances module
- Split expense read schema from form schema (no superRefine on read) — fixes list-emptying ZodError
- Extend invalidateBillCaches/invalidatePaymentCaches to overview/monthlyBalance/byCategory/projection/ownerDistribution + reserves
- parseList(safeParse) helper across list hooks; remove eslint-disable + paginated unwrap in client.ts
- global-search → real ROUTES; main-layout → useCurrentUser; remove dead code (Bell, re-export, tag-fee/late-fee helpers); split-based dates in legacy modals

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar `frontend/CLAUDE.md` mencionando o `LeaseFormModal` único e o endpoint atômico. Atualizar a memória do projeto (`project_parcelas_empty_zod_bug` / criar nota sobre `parseList` como política única de parsing de listas). O próximo plano pode assumir: criação de lease é atômica e centralizada em um modal/hook; `condominium_id` defaulta em todos os serializers condo-scoped; caches de dinheiro do módulo novo invalidam consistentemente; política de parse de lista é `parseList`/`safeParse`.
