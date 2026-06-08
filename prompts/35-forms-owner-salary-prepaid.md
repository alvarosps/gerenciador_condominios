# Sessão 35 — Forms: `owner` no Apartamento + `is_salary_offset`/`prepaid_until` na Locação

> **Feature**: Módulo Financeiro do Condomínio (Saídas, Saldo, Reserva e Distribuição)
> **Sessões da feature**: 34 → 50 (esta é a **35**, a **Fase 1b** do faseamento — design §14). Fase 1b expõe **nos modais de form** os campos que os serializers **já têm** mas o front **não renderiza**: `owner` (Apartamento) e `is_salary_offset`/`prepaid_until` (Locação), com gating `is_staff` e atualização dos testes de form. **Sem backend novo, sem `finances`, sem migration, sem serviço.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §6 inteira — não-invasivo; §2 decisão #14; §7 linhas Adriana/Rosa; §17 apêndice PROD; §18 "Folha"/"Receita/collectibility")**: `@docs/plans/2026-06-06-condominium-finance-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (ler conventions; **NÃO editar** — o orquestrador cuida de ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### O que o design pede desta sessão (§6, último bullet "Forms"; §14 Fase 1b)

> "expor `owner` (Apartamento) e `is_salary_offset`/`prepaid_until`/vínculo de funcionário (Locação) — serializers já têm os campos; **os MODAIS de form não os renderizam** (Fase 1b), com gating `is_staff` e atualização dos testes de form existentes."

**Casos reais que isto destrava** (§7/§17): registrar `prepaid_until` da **Adriana (836/113)** (hoje `null`, "a registrar via form"); marcar `is_salary_offset` da **Rosa (850/205)**; setar `owner` (Tiago `836/101,103` / Alvaro `836/200,203`) — todos já corretos em PROD, mas o form precisa **poder** editá-los. A regra `owner IS NULL = condomínio` já produz a receita certa (§17) — esta sessão só dá a UI para mantê-la, **sem mudar o income SSOT**.

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Modal de Apartamento (alvo de edição)** | `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx:48-57` (`apartmentFormSchema` local) + `:69-104` (`defaultValues`/`reset`) + `:341-354` (último `FormField`, onde inserir o de owner) | O `Select` de `building_id` (`:150-177`) é o template **exato** do `Select` de `owner` (numérico, `onValueChange`→`Number`, `value`→`String`). O schema local **NÃO** tem `owner_id` — adicionar |
| **Modal de Locação (alvo de edição)** | `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx:71-87` (`leaseFormSchema` local) + `:117-181` (`defaultValues`/`reset` create+edit) + `:294-307` (objeto `payload`) | Schema local e `payload` **NÃO** carregam `prepaid_until`/`is_salary_offset` — adicionar. O `FormField` de `last_rent_increase_date` (`:706-729`, `isEditMode &&`) é o template do `Input type="date"`; o `Checkbox` de `cleaning_fee_paid` (`:766-785`) é o template do toggle |
| **Gating `is_staff` (fonte canônica)** | `frontend/app/(dashboard)/financial/daily/page.tsx:18` (`import { useAuthStore }`), `:29-30` (`const { user } = useAuthStore(); const isAdmin = user?.is_staff ?? false;`) | Padrão idêntico em 7 páginas financeiras. **Reusar** `isAdmin = user?.is_staff ?? false` |
| **`User.is_staff` (store)** | `frontend/store/auth-store.ts:7-13` (`interface User { … is_staff: boolean }`) | Fonte do flag; nunca derivar de outro lugar |
| **Hook `usePersons` (popular o Select de owner)** | `frontend/lib/api/hooks/use-persons.ts:7-18` (`usePersons()` → `Person[]`, `page_size: 10000`) | Lista para o `<SelectItem>` de proprietário. **Não** criar hook novo |
| **`Person` schema** | `frontend/lib/schemas/person.schema.ts` (`Person` tem `id`/`name`) | `owner` é `{ id, name }` (`apartment.schema.ts:26`) |
| **Schema `apartment` (já tem owner)** | `frontend/lib/schemas/apartment.schema.ts:26-27` (`owner: {id,name}.nullable().optional()`, `owner_id: number.nullable().optional()`) | **Já existe** — não tocar o schema central |
| **Schema `lease` (já tem os campos)** | `frontend/lib/schemas/lease.schema.ts:49-50` (`prepaid_until: string.nullable().optional()`, `is_salary_offset: boolean.optional()`) | **Já existe** — não tocar o schema central |
| **Serializer Apartamento (write)** | `core/serializers.py:124-130` (`owner_id = PrimaryKeyRelatedField(source="owner", write_only, required=False, allow_null=True)`), `:148-149` (em `fields`) | Confirma: o back **aceita** `owner_id` (e `null`). **Não tocar** |
| **Serializer Locação (write)** | `core/serializers.py:398-399` (`"prepaid_until"`, `"is_salary_offset"` em `fields`) | Confirma: o back **aceita** ambos. **Não tocar** |
| **Hook `useCreateApartment` (BUG load-bearing)** | `frontend/lib/api/hooks/use-apartments.ts:57` (`Omit<Apartment, … 'owner' | 'owner_id' …>`) + `:59` (`apartmentSchema.omit({ id, building, furnitures }).parse(data)`) | O POST **descarta `owner_id`** hoje (o `Omit` tira do tipo; o `.parse` só preserva chaves do schema, e `owner_id` está no schema — mas o tipo do `mutationFn` o exclui ⇒ o form não consegue passá-lo). **Corrigir** para `owner_id` fluir no create (ver §Especificação) |
| **Hook `useUpdateApartment` (OK no PUT)** | `frontend/lib/api/hooks/use-apartments.ts:78-88` (`Partial<Apartment> & {id}`; remove só `building`/`furnitures`/`active_lease`/`owner`, **mantém `owner_id`**) | O PUT **já** carrega `owner_id`. Não precisa mudar para edição |
| **Hook `useCreateLease`/`useUpdateLease`** | `frontend/lib/api/hooks/use-leases.ts:58` (`Omit<Lease,'id'|'apartment'|'responsible_tenant'|'tenants'|'final_date'|'rental_value'|'resident_dependent'>`), `:77` (`Partial<Lease> & {id}`) | `prepaid_until`/`is_salary_offset` **não** estão no `Omit` ⇒ já fluem; mas o **form** monta um `payload` literal (`:294-307`) que os exclui — incluí-los no payload |
| **Teste do modal de Apartamento** | `frontend/app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx:9-41` (mocks de hooks), `:85-92` (asserts de campos) | **Adicionar** `vi.mock('@/lib/api/hooks/use-persons')` + `vi.mock('@/store/auth-store')`; novos casos de owner + gating |
| **Teste do modal de Locação** | `frontend/app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx:9-64` (mocks), `:125-137` (asserts) | **Adicionar** mock de `useAuthStore`; novos casos de prepaid/salary-offset + gating |
| **`renderWithProviders` / test-utils** | `frontend/tests/test-utils.tsx` | Wrapper dos testes de componente (já usado por ambos os arquivos) |

### Confirmação cross-stack (já verificada — não re-investigar)

- **Apartamento**: schema central + serializer já têm `owner`/`owner_id`. **Falta**: render no modal + o `mutationFn` de **create** aceitar/repassar `owner_id`.
- **Locação**: schema central + serializer já têm `prepaid_until`/`is_salary_offset`. **Falta**: render no modal + incluir no `payload` literal do `handleSubmit`.
- **"Vínculo de funcionário"**: o FK que liga funcionário↔lease é **`Employee.lease`** e vive no app **`finances`** (design §5.2), criado na **Sessão 34**. O `LeaseSerializer` (`core/serializers.py:372-400`) **não** tem campo de employee, e nenhum endpoint/serializer de `finances` existe ainda. Portanto a edição desse vínculo pertence ao **form de `Employee` (Fase 3, Sessão ~44–46)**, do lado do `finances`, **não** ao form de Locação. **Esta sessão NÃO implementa vínculo de funcionário** (ver §NÃO fazer).

---

## Escopo

### Arquivos a modificar
- `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx` — adicionar `owner_id` ao `apartmentFormSchema` local + `defaultValues`/`reset` + `FormField` `Select` de proprietário (gated `is_staff`); incluir `owner_id` no objeto submetido.
- `frontend/lib/api/hooks/use-apartments.ts` — corrigir `useCreateApartment` para que `owner_id` flua no POST (ver §Especificação). `useUpdateApartment` já carrega `owner_id` — **não** alterar a menos que o type-check exija.
- `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` — adicionar `prepaid_until` (`Input type="date"`) e `is_salary_offset` (`Checkbox`) ao `leaseFormSchema` local + `defaultValues`/`reset` (create **e** edit) + os dois `FormField` (gated `is_staff`); incluir ambos no `payload` do `handleSubmit`.
- `frontend/app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx` — mocks de `use-persons` + `auth-store`; casos de owner + gating.
- `frontend/app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx` — mock de `auth-store`; casos de prepaid/salary-offset + gating.

### Arquivos que NÃO devem ser tocados
- `frontend/lib/schemas/apartment.schema.ts` e `lease.schema.ts` — **já têm** os campos (apartment.schema.ts:26-27; lease.schema.ts:49-50). Não duplicar/mexer.
- `core/serializers.py`, `core/models.py`, `core/views.py`, qualquer migration — o backend **já expõe** tudo.
- `frontend/store/auth-store.ts` — `is_staff` já existe.

### NÃO fazer (pertence a outras sessões)
- **Nenhum** modelo, serviço, serializer ou endpoint novo. **Nada** do app `finances`. **Sem** migration. (App `finances`/`Condominium`/`Building.condominium` = **Sessão 34**; serviços/serializers/viewsets do `finances` = Fases 2–6, Sessões 36+.)
- **Vínculo de funcionário (Employee↔Lease)**: NÃO implementar aqui. O FK `Employee.lease` é do `finances` (design §5.2), exposto no **form de Employee** (Fase 3 — Sessões ~44–46). O form de Locação não ganha campo de employee nesta sessão.
- **NÃO** alterar lógica de cobrabilidade, `RentScheduleService`, cache, signals, dashboard, projeção (Sessões 36+).
- **NÃO** mexer no income SSOT nem migrar owner (design §6/§14: não-invasivo, "sem migração de owner").
- **NÃO** editar `prompts/SESSION_STATE.md` nem `prompts/ROADMAP.md` (orquestrador). A nota de handoff abaixo descreve **o que** registrar; o orquestrador aplica.
- **NÃO** adicionar dependência nova (tudo já existe: RHF, Zod, Shadcn `Select`/`Checkbox`/`Input`, `usePersons`, `useAuthStore`).

---

## Especificação

### A. Modal de Apartamento — campo `owner`

1. **Schema local** (`apartmentFormSchema`, `apartment-form-modal.tsx:48-57`): adicionar
   `owner_id: z.number().nullable().optional()`. (O schema central já o tem; aqui é o schema do **form**.)
2. **`defaultValues`** (`:69-78`) e o ramo `reset` de edição (`:91-100`): adicionar
   `owner_id: apartment?.owner?.id ?? null` (default `null` no create). Garantir que o `else`/`reset()` zere o campo.
3. **Render — `FormField` `Select` de proprietário**, inserido **após** o último field existente
   (`last_rent_increase_date`, `:341-354`), **gated por `is_staff`**:
   - `const { user } = useAuthStore(); const isAdmin = user?.is_staff ?? false;` (mesma forma de `daily/page.tsx:29-30`).
   - `const { data: persons } = usePersons();`
   - Renderizar o bloco **somente quando `isAdmin`** (`{isAdmin && (<FormField …/>)}`).
   - `Select` espelhando o de `building_id` (`:150-177`): `onValueChange` mapeia o valor especial
     **`"none"`** → `null` (condomínio) e qualquer outro → `Number(value)`; `value` = `field.value ? String(field.value) : 'none'`.
   - Primeiro `<SelectItem value="none">Condomínio (sem proprietário)</SelectItem>`, depois um item por `person` (`value={String(p.id)}`, label `p.name`).
   - `<FormLabel>Proprietário</FormLabel>` + `<FormDescription>` em PT: "Vazio = receita do condomínio. Definir proprietário repassa o aluguel (não conta como receita)."
   - **`value` do `SelectItem` nunca pode ser string vazia** (Radix proíbe) — por isso o sentinela `"none"`.
4. **Submissão**: incluir `owner_id: values.owner_id ?? null` tanto no `updateMutation.mutateAsync` (`:109-112`)
   quanto no `createMutation.mutateAsync` (`:115-118`).
5. **Hook `useCreateApartment`** (`use-apartments.ts:53-69`): hoje o `mutationFn` é
   `Omit<Apartment, 'id'|'building'|'furnitures'|'is_rented'|'owner'|'owner_id'|'lease'>` e o corpo faz
   `apartmentSchema.omit({ id, building, furnitures }).parse(data)`. **Corrigir** para `owner_id` fluir:
   remover `'owner_id'` do `Omit` (manter `'owner'`/`'lease'`/`'is_rented'`/`'building'`/`'furnitures'`),
   de modo que o tipo aceite `owner_id` e o `.parse` (que mantém chaves do schema, incl. `owner_id`)
   o envie no POST. **Não** introduzir `as`/`!`; ajustar o tipo na raiz. (`'lease'` não é chave de
   `Apartment` — se o type-check reclamar do `Omit` de uma chave inexistente, remover `'lease'` também;
   manter o conjunto **mínimo correto**.)

### B. Modal de Locação — `prepaid_until` + `is_salary_offset`

1. **Schema local** (`leaseFormSchema`, `lease-form-modal.tsx:71-87`): adicionar
   `prepaid_until: z.string().nullable().optional()` e `is_salary_offset: z.boolean().optional()`.
2. **`defaultValues`** (`:119-132`), ramo **edit** (`:145-159`) e ramo **create/else** (`:162-176`):
   - edit: `prepaid_until: lease.prepaid_until ?? null`, `is_salary_offset: lease.is_salary_offset ?? false`.
   - create: `prepaid_until: null`, `is_salary_offset: false`.
3. **Render — gated `is_staff`** (`isAdmin = user?.is_staff ?? false`), na seção "Período e Valores"
   (após `deposit_amount`, `:731-760`, antes do `<Separator/>` de "Confirmações"):
   - `is_salary_offset`: `Checkbox` espelhando `cleaning_fee_paid` (`:766-785`):
     `<FormLabel>Aluguel compensado por salário</FormLabel>` +
     `<FormDescription>` PT: "Inquilino-funcionário: o aluguel é abatido na folha. Exclui esta locação da receita do condomínio."
   - `prepaid_until`: `Input type="date"` espelhando `last_rent_increase_date` (`:706-729`):
     `value={field.value ?? ''}`, `onChange={(e) => field.onChange(e.target.value || null)}`;
     `<FormLabel>Pré-pago até</FormLabel>` +
     `<FormDescription>` PT: "Meses até esta data já estão pagos (não cobrados). Deixe vazio se não houver pré-pagamento."
   - Os dois blocos só renderizam quando `isAdmin`.
4. **Submissão**: no objeto `payload` (`:294-307`) incluir
   `prepaid_until: values.prepaid_until ?? null` e `is_salary_offset: values.is_salary_offset ?? false`.
   Eles fluem tanto no create (`createMutation.mutateAsync(payload)`, `:325`) quanto no update
   (`updatePayload`, `:317-321`). `useCreateLease`/`useUpdateLease` (`use-leases.ts:58,77`) **já** aceitam
   esses campos (não estão no `Omit`) — **não** alterar os hooks de lease.

### Edge-cases obrigatórios (design §18 "Receita/collectibility" e "Folha")

- **owner = `null` (Condomínio)**: selecionar "Condomínio (sem proprietário)" envia `owner_id: null` (não string vazia, não `"none"` cru). É o caso default e o mais comum (Raul & Célia, §17).
- **owner setado**: selecionar uma pessoa envia o `id` numérico (Tiago/Alvaro repassam aluguel — saem da receita, §6).
- **`prepaid_until` vazio**: envia `null` (Adriana hoje; o form deve permitir **gravar uma data** e também **limpar** de volta para `null`).
- **`is_salary_offset` marcado/desmarcado**: booleano explícito (Rosa = `true`; default `false`).
- **Não-admin (`is_staff=false`)**: nenhum dos campos novos renderiza (gating de escrita — design §6/security.md). O resto do form continua funcionando.
- **Edição preenche os valores atuais**: abrir o modal de um apartamento com `owner` setado pré-seleciona a pessoa; abrir uma locação com `prepaid_until`/`is_salary_offset` pré-preenche data/checkbox.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`tests/CLAUDE.md`): mockar **apenas fronteiras externas**. Nos testes de componente isso = os **hooks de dados** (`useCreateApartment`/`useUpdateApartment`/`useBuildings`/`useFurniture`/`usePersons`/`useCreateLease`/`useUpdateLease`/`useAvailableApartments`/`useTenants`) e o **store** `useAuthStore` (fronteira de estado de auth) via `vi.mock`/`vi.spyOn` — **exatamente** como os testes existentes já mockam os hooks (`apartment-form-modal.test.tsx:9-41`, `lease-form-modal.test.tsx:9-64`). **NUNCA** mockar RHF, Zod, Shadcn ou o componente sob teste. HTTP real não é exercido (componente isolado).

### 1. RED — escrever/expandir os testes primeiro

**`apartment-form-modal.test.tsx`** — adicionar:
- `vi.mock('@/lib/api/hooks/use-persons', …)` retornando `usePersons` mock (≥2 pessoas: ex. Tiago id 2, Alvaro id 3) e `vi.mock('@/store/auth-store', …)` com `useAuthStore` controlável por teste (`{ user: { is_staff: true|false } }`).
- [ ] **admin vê o campo**: `is_staff=true` → render mostra `Proprietário` (label) e a opção `Condomínio (sem proprietário)`.
- [ ] **não-admin não vê**: `is_staff=false` → `queryByText('Proprietário')` é `null`.
- [ ] **edição pré-seleciona owner**: `apartment.owner = { id: 2, name: 'Tiago' }` + `is_staff=true` → o `Select` reflete Tiago (asserir via texto/`combobox` value).
- [ ] **create com owner**: selecionar uma pessoa e submeter → `useCreateApartment().mutateAsync` chamado com `owner_id: <id numérico>` (capturar via mock `mutateAsync`).
- [ ] **create como condomínio**: manter "Condomínio (sem proprietário)" e submeter → `mutateAsync` chamado com `owner_id: null` (nunca `"none"`/`""`).
- [ ] **regressão**: os 9 testes existentes (`:55-113`) continuam verdes (campos required, título, furniture, cancel).

**`lease-form-modal.test.tsx`** — adicionar:
- `vi.mock('@/store/auth-store', …)` com `useAuthStore` controlável.
- [ ] **admin vê os campos**: `is_staff=true` → `Aluguel compensado por salário` e `Pré-pago até` presentes.
- [ ] **não-admin não vê**: `is_staff=false` → ambos `queryByText` retornam `null`.
- [ ] **edição pré-preenche**: `lease.is_salary_offset=true` + `lease.prepaid_until='2026-07-01'` + `is_staff=true` → checkbox marcado e input date com `2026-07-01`.
- [ ] **submit inclui os campos**: marcar salary-offset + setar uma data e submeter → `useCreateLease().mutateAsync` (ou `useUpdateLease` no modo edit) chamado com `is_salary_offset: true` e `prepaid_until: '<YYYY-MM-DD>'`.
- [ ] **limpar prepaid**: editar uma locação com `prepaid_until` setado, limpar o input e submeter → payload com `prepaid_until: null`.
- [ ] **regressão**: os 11 testes existentes (`:78-150`) continuam verdes.

> Rodar (devem **falhar** — campos/casos ainda não existem):
> ```bash
> cd frontend ; npx vitest run "app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx" "app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx"
> ```

### 2. GREEN — implementar o mínimo

Aplicar §A (apartamento: schema local + owner Select gated + `owner_id` na submissão + correção do `useCreateApartment`) e §B (locação: schema local + 2 fields gated + payload). Rodar até verde:
```bash
cd frontend ; npx vitest run "app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx" "app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx"
```

### 3. REFACTOR — limpar sem mudar comportamento
- Sem duplicação: reusar a forma `isAdmin = user?.is_staff ?? false` (não criar helper novo — é uma linha, KISS); reusar `usePersons` (não criar hook). Selects numéricos seguem o template de `building_id`/`responsible_tenant_id` já no arquivo.
- Sentinela `"none"` definido como constante local (`const OWNER_NONE = 'none'`) se usado em 2+ lugares (DRY); senão, inline.
- Garantir que o `else { formMethods.reset(); }` do apartamento (`:101-103`) zere `owner_id` (o `reset()` sem args usa `defaultValues`, que agora inclui `owner_id: null`).

### 4. VERIFY — gate (escopo dos arquivos tocados)
```bash
cd frontend
npx vitest run "app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx" "app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx"
npm run type-check
npx eslint "app/(dashboard)/apartments/_components/apartment-form-modal.tsx" "app/(dashboard)/leases/_components/lease-form-modal.tsx" "lib/api/hooks/use-apartments.ts" "app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx" "app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx"
```
Zero erros **e** zero warnings em Vitest, TypeScript e ESLint. (`type-check` roda em todo o front — o tipo de `useCreateApartment` mudou, então rodar o `tsc` completo é obrigatório para pegar consumidores.)

---

## Constraints

- **Backend intocado**: zero mudança em `core/` (serializers já expõem `owner_id`/`prepaid_until`/`is_salary_offset`). Zero `finances`. Zero migration. Zero serviço.
- **Schemas centrais intocados**: `apartment.schema.ts`/`lease.schema.ts` já têm os campos — não duplicar nem alterar.
- **Gating de escrita** (security.md): os campos novos só renderizam para `is_staff` (admin). Não é segurança real (o backend valida via `FinancialReadOnly`/permissões), mas o front **deve** esconder edição para não-admin — espelhar o padrão das 7 páginas financeiras.
- **Sem suppressions**: proibido `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `# noqa`. Corrigir o tipo na raiz (ex.: o `Omit` do `useCreateApartment`). **Sem `as`/`!` em código de produção**; em testes, `as never` é o idioma já usado para fixtures de mock (`apartment-form-modal.test.tsx:32`) — manter restrito a fixtures/boundary, como nas sessões anteriores.
- **Sem re-exports / barrel / shim**; imports diretos da fonte (`@/lib/api/hooks/use-persons`, `@/store/auth-store`).
- **Sem `from __future__`/`TYPE_CHECKING`** (regra backend — não se aplica ao TS, mas vale o espírito: importar tipos diretamente, `import type`).
- **TanStack/Forms**: nada de `useState` para server state; selects numéricos com sentinela `"none"` (Radix proíbe `value=""`). `mutationFn` invalida queries no `onSuccess` (já feito nos hooks existentes — não duplicar).
- **i18n**: textos de UI/erros em **Português**; logs/identificadores em **Inglês**.
- **Datas TZ-safe**: `prepaid_until` é string `YYYY-MM-DD` (DateField) — não converter para `Date`/UTC; passar a string crua ao backend (o `Input type="date"` já entrega `YYYY-MM-DD`).
- **Design principles** (`.claude/rules/design-principles.md`): SOLID/DRY/KISS/YAGNI; refactor completo do `useCreateApartment` (atualizar o tipo e todos os call sites se o `tsc` apontar); sem campos especulativos (nada de employee link aqui).

---

## Critérios de Aceite (binários)

- [ ] Modal de Apartamento renderiza o `Select` "Proprietário" **apenas** para `is_staff`, com opção "Condomínio (sem proprietário)" + uma por `Person` de `usePersons`.
- [ ] `apartmentFormSchema` local tem `owner_id`; `defaultValues`/`reset` (create+edit) tratam `owner_id` (default `null`, edição pré-seleciona `apartment.owner.id`).
- [ ] Submissão envia `owner_id` numérico ao selecionar pessoa e `owner_id: null` ao selecionar "Condomínio" — no **create** e no **update**.
- [ ] `useCreateApartment` (`use-apartments.ts`) corrigido para que `owner_id` flua no POST (tipo + `.parse`), **sem** `as`/`# type: ignore`/`eslint-disable`.
- [ ] Modal de Locação renderiza `is_salary_offset` (Checkbox) e `prepaid_until` (Input date) **apenas** para `is_staff`.
- [ ] `leaseFormSchema` local tem `prepaid_until`/`is_salary_offset`; `defaultValues`/`reset` (create+edit) os tratam; edição pré-preenche.
- [ ] `payload` do `handleSubmit` da Locação inclui `prepaid_until` (ou `null`) e `is_salary_offset` (booleano) — create e update. Hooks de lease **não** alterados.
- [ ] Edge-cases cobertos por teste: owner=null (condomínio), owner setado, prepaid vazio→`null`, prepaid setado, salary-offset on/off, não-admin não vê os campos, edição pré-preenche.
- [ ] Todos os testes de form (apartamento + locação) verdes, **incluindo** os 9 + 11 existentes (regressão), com os mocks de `use-persons`/`auth-store` adicionados.
- [ ] `npm run type-check` limpo (front inteiro), `npx eslint` limpo nos 5 arquivos tocados — **zero erros e zero warnings**.
- [ ] Nenhum arquivo de `core/`, `finances/`, migration, schema central (`apartment.schema.ts`/`lease.schema.ts`), `auth-store.ts` ou de outra sessão alterado. Nenhum campo de **funcionário** adicionado ao form de Locação.

---

## Handoff

1. Rodar e confirmar verde (escopo desta sessão):
   ```bash
   cd frontend
   npx vitest run "app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx" "app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx"
   npm run type-check
   npx eslint "app/(dashboard)/apartments/_components/apartment-form-modal.tsx" "app/(dashboard)/leases/_components/lease-form-modal.tsx" "lib/api/hooks/use-apartments.ts" "app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx" "app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx"
   ```
2. Rodar `/audit` (skill `audit`) contra a seção **Critérios de Aceite** e corrigir qualquer gap antes de fechar.
3. Reportar ao orquestrador para registrar no `SESSION_STATE.md` (NÃO editar você mesmo) — fornecer:
   - Linha da **Sessão 35** (status **concluída**), **Arquivos Modificados**: `apartment-form-modal.tsx`, `lease-form-modal.tsx`, `use-apartments.ts`, e os 2 arquivos de teste.
   - **Contratos cross-session honrados**: serializers `owner_id`/`prepaid_until`/`is_salary_offset` **consumidos sem alteração** (`core/serializers.py:124-130,398-399`); income SSOT/`collectible_leases` **inalterados** (não-invasivo, design §6). Forms agora permitem registrar Adriana (`prepaid_until`), Rosa (`is_salary_offset`) e owner (Tiago/Alvaro), pré-requisito real das Fases 4–6.
   - **Nota**: vínculo de funcionário (Employee↔Lease) **não** entrou (é `finances`/form de Employee, Fase 3 — Sessão ~44–46); `useCreateApartment` corrigido para repassar `owner_id` (bug pré-existente que silenciava o campo no POST); gating `is_staff` em ambos os modais.
4. Commitar (a partir de `master`, criar branch se necessário):
   ```
   feat(frontend): expose owner on apartment form + prepaid_until/is_salary_offset on lease form (is_staff gated)

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **36 — Backend `finances` (Fase 2: Category/BillingAccount/Bill/…)** ou conforme a ordem do ROADMAP (`34→35`; cross-phase: models → services → serializers/viewsets → frontend). Esta sessão (35) depende só do **core** (Sessão 34 idealmente concluída, mas pode rodar em paralelo após 34, pois não toca `finances`).
