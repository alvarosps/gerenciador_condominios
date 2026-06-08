# Sessão 54 — Frontend: wizard combinado `TenantLeaseOnboardingWizard` + hook + schema

> **Feature**: Fluxo "Novo inquilino + contrato" (web) — `docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
> **Sessões**: 51 → 52 → 53 → **54** → 55. Esta cria o **wizard** (passos 0–5), o **hook** `useOnboardTenantLease` e o **schema combinado**, consumindo o contrato da API (S52) e os utils/componentes compartilhados (S53).
> **Depende de**: **S52** (endpoint `POST /api/onboarding/tenant-lease/`) **e S53** (utils/`resident-dependent-field`/`leaseValuesSchemaShape`/remoção de email/phone_alternate). **Se S52 ou S53 não estiverem concluídas, PARE.**
> **Branch**: `feat/tenant-lease-onboarding`.

---

## Contexto

Ler antes de codar:
- **Design doc** (ler §4.3 passos 0–5, §5 G5/G7, §6 erros): `@docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado**: `@prompts/SESSION_STATE.md` (ler **contrato da API S52** + **contratos S53** verbatim)
- **Frontend rules**: `@frontend/CLAUDE.md`, `.claude/rules/{architecture,coding-standards,design-principles}.md`

### Exemplares (arquivo:symbol — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| Wizard multi-step (Dialog + Stepper + RHF por passo + cancel confirm) | `frontend/app/(dashboard)/tenants/_components/wizard/index.tsx` + `types.ts` (WIZARD_STEPS, validação por passo via `trigger`) | Padrão BASE do wizard de onboarding. |
| Form de contrato (campos/UX, select de apto, 2º inquilino) | `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` | Campos/effects do contrato (agora consumindo utils da S53). |
| Apartamentos disponíveis | `frontend/lib/api/hooks/use-apartments.ts:122` (`useAvailableApartments`) | Popular o select do passo 3. |
| Inquilinos + contratos (p/ "sem contrato ativo") | `frontend/lib/api/hooks/use-tenants.ts` (`useTenants`) + `use-leases.ts` (`useLeases`); derivação em `frontend/app/(dashboard)/tenants/page.tsx:337-348` (`leaseByTenantId` → `tenantsWithoutLease`) | Fonte do select de inquilino existente (passo 0). |
| Utils/components compartilhados (S53) | `@/lib/utils/lease-derivations`, `@/lib/utils/date`, `@/lib/utils/helpers` (`calculateTagFee`), `@/lib/schemas/lease.schema` (`leaseValuesSchemaShape`), `@/app/(dashboard)/_components/shared/resident-dependent-field` | **Reusar** (não duplicar). |
| Hook de mutation + invalidação | `frontend/lib/api/hooks/use-leases.ts` (`useCreateLease` invalida `leases.all`/`apartments.all`/`dashboard.all`) | Forma do `useOnboardTenantLease`. |
| Query keys | `frontend/lib/api/query-keys.ts` | `tenants.all`, `leases.all`, `apartments.all`, `dashboard.all`. |
| MSW handlers | `frontend/tests/mocks/handlers.ts` | Adicionar handler do onboarding (`*/onboarding/tenant-lease/`). |
| Error mapping PT | `frontend/lib/utils/error-handler.ts` (`getErrorMessage`) | Toast PT + pular para passo culpado. |

---

## Escopo

### Arquivos a criar
- `frontend/lib/schemas/tenant-lease-onboarding.schema.ts` — `tenantLeaseOnboardingSchema` + tipo `TenantLeaseOnboardingFormValues` (compõe campos de inquilino + `leaseValuesSchemaShape` + apto/datas/number_of_tenants + residente).
- `frontend/lib/api/hooks/use-onboarding.ts` — `useOnboardTenantLease`.
- `frontend/app/(dashboard)/_components/tenant-lease-onboarding/index.tsx` — `TenantLeaseOnboardingWizard`.
- `frontend/app/(dashboard)/_components/tenant-lease-onboarding/steps/*.tsx` — passos 0–5 (start, tenant-required, tenant-optional, lease-property, lease-values, review).
- `frontend/app/(dashboard)/_components/tenant-lease-onboarding/use-onboarding-tenants.ts` — helper que cruza `useTenants`+`useLeases` → inquilinos sem contrato ativo + função de prefill.
- Testes: `frontend/lib/schemas/__tests__/tenant-lease-onboarding.schema.test.ts`, `frontend/lib/api/hooks/__tests__/use-onboarding.test.tsx`, `frontend/app/(dashboard)/_components/tenant-lease-onboarding/__tests__/wizard.test.tsx`.

### Arquivos a modificar
- `frontend/tests/mocks/handlers.ts` — handler do onboarding (201 `{tenant, lease}`; 400 namespeado para cenários de teste).
- `frontend/lib/api/query-keys.ts` — só se faltar alguma key (provavelmente já existem todas).

### NÃO fazer
- **NÃO** montar o CTA no dashboard nem o passo 6 (PDF) — é a **S55**. (Este wizard expõe `onSuccess(tenant, lease)`; a S55 liga o CTA e o passo de PDF.)
- **NÃO** chamar `useUpdateTenant` para inquilino existente (ela remove `dependents`); o update acontece no endpoint de onboarding (S52).
- **NÃO** gerar PDF aqui. Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção; sem barrel/re-export.

---

## Especificação

### Schema combinado (`tenant-lease-onboarding.schema.ts`)
- Campos de inquilino (obrigatórios): `name`, `is_company`, `cpf_cnpj`, `phone`, `profession`, `marital_status`, `due_day`; opcionais: `rg`, `dependents[]`, `furniture_ids[]`; **`id` opcional** (inquilino existente). **Sem** `email`/`phone_alternate` (removidos na S53).
- Campos de contrato: `apartment_id`, `number_of_tenants` (1|2), `start_date` (Date), `validity_months` (1–60) + `...leaseValuesSchemaShape` (S53).
- Residente: `resident_dependent_id?` **ou** `resident_dependent?: {name, phone}` (exclusivos; obrigar um quando `number_of_tenants===2` — `superRefine`).
- Reusar validadores existentes (`validateCpfCnpj`, `validateBrazilianPhone`) de `lib/schemas/tenant.schema.ts`/utils — **não** reescrever.

### Montagem do payload (→ body S52, verbatim)
```ts
const body = {
  tenant: { id, name, is_company, cpf_cnpj, rg, phone, profession, marital_status, due_day, dependents, furniture_ids },
  lease: { apartment_id, number_of_tenants, start_date: fmt(start_date), validity_months,
           rental_value, tag_fee, deposit_amount, cleaning_fee_paid, tag_deposit_paid, due_day,
           prepaid_until, is_salary_offset },   // SEM responsible_tenant_id / tenant_ids
  ...(residentNew ? { resident_dependent } : residentId ? { resident_dependent_id } : {}),
};
```
- `tenant.id` presente só quando inquilino existente. `start_date` formatado `YYYY-MM-DD` (date-fns). Campos admin (`prepaid_until`/`is_salary_offset`) só quando `is_staff`.

### `useOnboardTenantLease` (hook)
- `useMutation` → `apiClient.post("/onboarding/tenant-lease/", body)` → valida resposta `{tenant, lease}` (Zod) → retorna.
- `onSuccess`: `invalidateQueries` para `tenants.all`, `leases.all`, `apartments.all`, `dashboard.all`.
- Erros DRF namespeados (`{tenant|lease: ...}`) propagam para o wizard.

### Passos do wizard
0. **Início** — RadioGroup "Novo" | "Existente (sem contrato ativo)". Existente: select (busca) populado por `use-onboarding-tenants` (cruza `useTenants`+`useLeases` → `tenantsWithoutLease`, espelhando `tenants/page.tsx:337-348`). Ao escolher → **prefill** de todos os campos do inquilino. **Conversão (G7)**: a API de tenant retorna `furnitures` (nested) → mapear para `furniture_ids` (`furnitures.map(f => f.id)`); `dependents` nested → array do form. (Não usar `useUpdateTenant`.)
1. **Inquilino — obrigatórios** + recolhível `rg`.
2. **Inquilino — opcionais (recolhível)** — dependentes (`useFieldArray`, reusar `DependentFormList`) + mobília (grade de checkboxes; reusar o componente de mobília do wizard de inquilino se reaproveitável, senão compor com `useFurniture`).
3. **Contrato — imóvel & período** — `apartment` (de `useAvailableApartments`), `number_of_tenants` (1/2, ≤ `apartment.max_tenants`, **sempre enviado**), `start_date`, `validity_months`. Effects: auto-`rental_value` (`deriveRentalValue`), auto-`tag_fee` (`calculateTagFee`), auto-`due_day` (`deriveDueDayFromStartDate`) no modo criação. Se `number_of_tenants===2`: `resident-dependent-field` (S53) + exigir `apartment.rental_value_double` (validação PT).
4. **Contrato — valores & pagamentos** — `rental_value`/`tag_fee` (pré-preenchidos, editáveis), `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`, `due_day` (pré-preenchido); `prepaid_until`/`is_salary_offset` só se `is_staff`.
5. **Revisão** — resumo inquilino + contrato; submit → `useOnboardTenantLease`. **Erro namespeado** → `getErrorMessage` (toast PT) + **pular para o passo culpado** (`tenant.cpf_cnpj`→passo 1; `lease.apartment`→passo 3; etc.). **Sucesso** → `toast.success("Inquilino e contrato criados com sucesso")`, disparar `props.onSuccess?.(tenant, lease)` e **fechar** o wizard (`props.onOpenChange(false)`). *(O passo 6 — PDF opcional — é inserido pela S55, que substitui o fechamento imediato por um estado de sucesso interno antes de fechar.)*

> Validação por passo via `formMethods.trigger(campos do passo)` antes de avançar (padrão do wizard de inquilino). Cancel com confirmação (AlertDialog), como o wizard atual.

---

## TDD — Red → Green → Refactor → Verify

> **Mock policy** (`frontend/CLAUDE.md`): MSW no boundary de rede; hooks/components reais (não mockar `useOnboardTenantLease` no teste do wizard). `renderWithProviders`.

### 1. RED — testes primeiro
#### `lib/schemas/__tests__/tenant-lease-onboarding.schema.test.ts`
- [ ] Schema aceita payload mínimo válido (1 inquilino novo).
- [ ] `number_of_tenants===2` sem residente → inválido; com `resident_dependent_id` **ou** `resident_dependent` → válido; ambos → inválido.
- [ ] **Não** aceita `email`/`phone_alternate` (campos inexistentes).

#### `lib/api/hooks/__tests__/use-onboarding.test.tsx`
- [ ] `useOnboardTenantLease` faz POST com body **exato** (sem `responsible_tenant_id`/`tenant_ids`; `tenant.id` quando existente) — capturar body no handler MSW.
- [ ] `onSuccess` invalida `tenants.all`/`leases.all`/`apartments.all`/`dashboard.all` (spy em `invalidateQueries`).
- [ ] Erro 400 namespeado propaga.

#### `_components/tenant-lease-onboarding/__tests__/wizard.test.tsx`
- [ ] Fluxo novo: navega passos 0→5, validação por passo bloqueia avanço com campo faltando, submit chama POST (MSW) → `onSuccess` com `{tenant, lease}`.
- [ ] Fluxo existente: escolher inquilino → campos prefilled (incl. `furniture_ids` convertidos de `furnitures`); submit envia `tenant.id`.
- [ ] 2 inquilinos: residente novo → body com `resident_dependent`.
- [ ] Erro `lease.apartment` (handler 400) → toast PT + volta ao passo 3.

> Rodar (devem falhar):
> ```bash
> cd frontend && npx vitest run "lib/schemas/__tests__/tenant-lease-onboarding.schema.test.ts" \
>   "lib/api/hooks/__tests__/use-onboarding.test.tsx" \
>   "app/(dashboard)/_components/tenant-lease-onboarding/__tests__/wizard.test.tsx"
> ```

### 2. GREEN — implementar schema, hook, helper de inquilinos, wizard + passos, MSW handler.

### 3. REFACTOR — DRY
- Reusar `deriveRentalValue`/`deriveDueDayFromStartDate`/`calculateTagFee`/`parseLocalDate`/`leaseValuesSchemaShape`/`resident-dependent-field` (S53) — **zero** duplicação do `lease-form-modal`.
- Prefill (furnitures→furniture_ids) num único helper testável (`use-onboarding-tenants`).
- Mapa "campo de erro → passo" como constante nomeada.

### 4. VERIFY — gate (escopo desta sessão)
```bash
cd frontend
npx vitest run "lib/schemas/__tests__/tenant-lease-onboarding.schema.test.ts" \
  "lib/api/hooks/__tests__/use-onboarding.test.tsx" \
  "app/(dashboard)/_components/tenant-lease-onboarding/__tests__/wizard.test.tsx"
npm run type-check
npx eslint lib/schemas/tenant-lease-onboarding.schema.ts lib/api/hooks/use-onboarding.ts \
  "app/(dashboard)/_components/tenant-lease-onboarding" tests/mocks/handlers.ts
```

---

## Constraints
- **Body verbatim** do contrato S52 (sem `responsible_tenant_id`/`tenant_ids`; residente novo ⊕ existente). `tenant.id` só p/ existente.
- **G7**: prefill converte `furnitures`→`furniture_ids`; **não** usar `useUpdateTenant`.
- **DRY**: reusar utils/componentes da S53; não duplicar lógica do `lease-form-modal`.
- **G5**: `number_of_tenants` sempre enviado; `rental_value` pré-preenchido+editável; 2 inquilinos exige `rental_value_double`.
- Server state via TanStack; form via RHF+Zod; toasts PT via `getErrorMessage`. Campos admin gated por `is_staff`.
- Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção; sem barrel/re-export; `import type`; named exports.

## Critérios de Aceite (binários)
- [ ] `tenantLeaseOnboardingSchema` compõe inquilino + `leaseValuesSchemaShape` + apto/datas/residente; exige residente quando 2 inquilinos (exclusivo); sem email/phone_alternate.
- [ ] `useOnboardTenantLease` posta o body verbatim e invalida as 4 queries; erro namespeado propaga.
- [ ] Wizard (passos 0–5) funciona p/ novo e existente (prefill com conversão de mobília), valida por passo, monta payload correto (incl. residente novo/existente) e mapeia erro→passo.
- [ ] Handler MSW do onboarding adicionado; todos os testes verdes.
- [ ] `type-check` 0 erros; `eslint` 0 erros/0 warnings; sem suppressions. `useUpdateTenant` **não** usado p/ o update do existente.

## Handoff
1. Gate verde.
2. Atualizar `prompts/SESSION_STATE.md` (S54 concluída; arquivos; contrato `onSuccess(tenant, lease)` + path do wizard p/ S55).
3. `/audit` contra os Critérios de Aceite.
4. Commit:
   ```
   feat(frontend): tenant+lease onboarding wizard + useOnboardTenantLease + combined schema

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima: **S55 — CTA no dashboard + passo de PDF + e2e/polish/audit**.

---

### Contratos cross-session (S55 consome verbatim)
- `TenantLeaseOnboardingWizard` (em `app/(dashboard)/_components/tenant-lease-onboarding/index.tsx`) aceita props `{ open: boolean; onOpenChange(open): void; onSuccess?(tenant, lease): void }`. Nesta sessão, ao submeter com sucesso o wizard dispara `onSuccess` e **fecha**. A **S55** modifica o `index.tsx` para inserir o **passo 6 (success-step)** internamente (estado `created`) antes do fechamento, e monta o **CTA** (`OnboardingCta`) que controla `open`.
- `useOnboardTenantLease` retorna `{ tenant, lease }` (lease tem `id` p/ `useGenerateContract` na S55).
