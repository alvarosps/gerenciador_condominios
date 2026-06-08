# Sessão 53 — Frontend: extração DRY (derivações de contrato + dependente) + remoção de campos fantasma

> **Feature**: Fluxo "Novo inquilino + contrato" (web) — `docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
> **Sessões**: 51 → 52 → **53** → 54 → 55. Esta extrai a lógica compartilhada que o `lease-form-modal` já contém (para o wizard da S54 **reusar**, não duplicar — design §5 G9) e corrige o bug pré-existente de `email`/`phone_alternate` (design §5 G6 / decisão D4).
> **Independente** de S51/S52 (só frontend) — pode rodar em paralelo. **S54 depende desta + da S52.**
> **Branch**: `feat/tenant-lease-onboarding`.

---

## Contexto

Ler antes de codar:
- **Design doc** (ler §4.3 "Reuso/DRY", §5 G6/G9): `@docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Frontend rules**: `@frontend/CLAUDE.md`, `.claude/rules/{architecture,coding-standards,design-principles}.md`

### Exemplares (arquivo:symbol — LER e localizar a lógica a extrair)

| O que extrair/corrigir | Onde está hoje | Alvo |
|------------------------|----------------|------|
| Derivação de `rental_value` (single vs double por `number_of_tenants`) | `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` (effect que auto-popula `rental_value` a partir de `apartment.rental_value`/`rental_value_double`) | `frontend/lib/utils/lease-derivations.ts` → `deriveRentalValue(apartment, numberOfTenants): number` |
| Derivação de `due_day` a partir de `start_date` (modo criação) | `lease-form-modal.tsx` (effect `due_day = start_date.getDate()`) | `lease-derivations.ts` → `deriveDueDayFromStartDate(date): number` |
| `calculateTagFee(number_of_tenants)` | `frontend/lib/utils/helpers.ts` (já existe — **reusar**, não recriar) | manter; só garantir import único |
| `parseLocalDate` (evita UTC shift) | `lease-form-modal.tsx` (e possivelmente duplicado) | `frontend/lib/utils/date.ts` → `parseLocalDate(s): Date` (mover p/ fonte única; atualizar TODOS os consumidores) |
| Fragmento Zod de **valores do contrato** | `frontend/lib/schemas/lease.schema.ts` | exportar objeto reutilizável `leaseValuesSchemaShape` (campos `rental_value`, `tag_fee`, `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`, `due_day`, `prepaid_until`, `is_salary_offset`) consumido por `lease.schema.ts` **e** (S54) pelo schema combinado |
| Seleção/criação inline de **dependente residente** (2 inquilinos) | `lease-form-modal.tsx` (RadioGroup de dependentes + "novo" + campos inline) | `frontend/app/(dashboard)/_components/shared/resident-dependent-field.tsx` → componente apresentacional reutilizável |
| **Bug**: `email`/`phone_alternate` coletados mas descartados | `frontend/lib/schemas/tenant.schema.ts:25-27` + `frontend/app/(dashboard)/tenants/_components/wizard/contact-info-step.tsx` + wizard `index.tsx`/`types.ts` | **remover** esses campos do schema, do step e do submit |
| `useAvailableApartments` | `frontend/lib/api/hooks/use-apartments.ts:122` | reusar no wizard (S54) — só confirmar export |

> **IMPORTANTE — refator completo (`.claude/rules/design-principles.md`)**: ao mover `parseLocalDate`/derivações para utilitários, **atualizar TODOS os consumidores** (o `lease-form-modal` passa a importar do novo local) — sem shim/re-export/duplicata. O `lease-form-modal` deve continuar funcionando idêntico (mesmos efeitos), agora consumindo os utilitários.

---

## Escopo

### Arquivos a criar
- `frontend/lib/utils/lease-derivations.ts` — `deriveRentalValue`, `deriveDueDayFromStartDate`.
- `frontend/lib/utils/date.ts` — `parseLocalDate` (se ainda não existir uma fonte única; senão mover para a existente).
- `frontend/app/(dashboard)/_components/shared/resident-dependent-field.tsx` — componente de seleção/criação do 2º ocupante.
- Testes: `frontend/lib/utils/__tests__/lease-derivations.test.ts`, `frontend/lib/utils/__tests__/date.test.ts`, `frontend/app/(dashboard)/_components/shared/__tests__/resident-dependent-field.test.tsx`.

### Arquivos a modificar
- `frontend/lib/schemas/lease.schema.ts` — exportar `leaseValuesSchemaShape` e consumi-lo internamente (sem mudar o schema público existente).
- `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` — consumir `deriveRentalValue`/`deriveDueDayFromStartDate`/`parseLocalDate`/`resident-dependent-field` (substituir a lógica inline; comportamento idêntico).
- `frontend/lib/schemas/tenant.schema.ts` — **remover** `email` e `phone_alternate` (G6).
- `frontend/app/(dashboard)/tenants/_components/wizard/contact-info-step.tsx`, `.../wizard/index.tsx`, `.../wizard/types.ts` — remover os campos `email`/`phone_alternate` (UI + submit + tipos).

### NÃO fazer
- **NÃO** criar o wizard de onboarding nem o hook/endpoint (S54/S52).
- **NÃO** mudar o comportamento do `lease-form-modal` (só a fonte da lógica). 
- **NÃO** adicionar `email`/`phone_alternate` ao backend (decisão D4 = remover da UI).
- Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção; sem re-export/barrel.

---

## Especificação

### `lease-derivations.ts`
```ts
import type { Apartment } from "@/lib/schemas/apartment.schema";

export function deriveRentalValue(apartment: Apartment, numberOfTenants: number): number {
  // 2 inquilinos -> rental_value_double (obrigatório quando max_tenants===2); senão rental_value
  return numberOfTenants >= 2 ? (apartment.rental_value_double ?? apartment.rental_value) : apartment.rental_value;
}

export function deriveDueDayFromStartDate(date: Date): number {
  return date.getDate(); // 1..31
}
```
> Tipar contra os schemas existentes; sem `as`/`!` (usar `?? `/guards sob `noUncheckedIndexedAccess`).

### `date.ts` — `parseLocalDate`
Mover a implementação atual (que evita o shift de UTC ao parsear `YYYY-MM-DD`) para `frontend/lib/utils/date.ts` como fonte única e atualizar imports no `lease-form-modal` (e qualquer outro consumidor). Se já existir um util de data canônico, colocá-la lá.

### `leaseValuesSchemaShape` (em `lease.schema.ts`)
Exportar o **shape** (objeto de campos Zod) dos valores do contrato para reuso:
```ts
export const leaseValuesSchemaShape = {
  rental_value: z.coerce.number().nonnegative(),
  tag_fee: z.coerce.number().nonnegative(),
  deposit_amount: z.coerce.number().nonnegative().optional(),
  cleaning_fee_paid: z.boolean().default(false),
  tag_deposit_paid: z.boolean().default(false),
  due_day: z.coerce.number().int().min(1).max(31),
  prepaid_until: z.string().optional(),     // admin
  is_salary_offset: z.boolean().default(false), // admin
};
```
> Ajustar tipos/transforms ao que `lease.schema.ts` já usa (coerção number/string). O `leaseSchema` existente passa a compor `leaseValuesSchemaShape` (sem alterar seu contrato público).

### `resident-dependent-field.tsx`
Componente apresentacional (sem `apiClient`) que recebe a lista de dependentes do inquilino (existentes) + callbacks e renderiza: RadioGroup (dependentes existentes ⊕ "Adicionar novo") e, em "novo", campos `name`/`phone` (formatados) — produzindo `{ resident_dependent_id }` (existente) **ou** `{ resident_dependent: {name, phone} }` (novo). Espelhar a UX atual do `lease-form-modal`, mas **sem** o PATCH (a S54 só monta o payload; a criação é atômica no backend). Reaproveitar `formatPhone` de `lib/utils/formatters.ts`.

### Remoção de `email`/`phone_alternate` (G6/D4)
- `tenant.schema.ts`: remover os 2 campos (e validadores associados).
- `contact-info-step.tsx`: remover os inputs de email e telefone alternativo (deixar só `phone`).
- `wizard/index.tsx` + `types.ts`: remover do schema do form, dos defaults e do payload de submit.
- Atualizar testes do wizard de inquilino que referenciem esses campos.

---

## TDD — Red → Green → Refactor → Verify

> **Mock policy** (`frontend/CLAUDE.md`): testes unitários puros para utils; componente via `renderWithProviders`; MSW só onde houver rede (não há aqui). Sem mock de internals.

### 1. RED — testes primeiro
#### `lib/utils/__tests__/lease-derivations.test.ts`
- [ ] `deriveRentalValue(apt, 1)` → `apt.rental_value`.
- [ ] `deriveRentalValue(apt, 2)` → `apt.rental_value_double` quando presente; fallback `rental_value` quando ausente.
- [ ] `deriveDueDayFromStartDate(new Date(2026, 5, 15))` → `15`.

#### `lib/utils/__tests__/date.test.ts`
- [ ] `parseLocalDate("2026-06-15")` → `Date` local com `getDate()===15` (sem shift de fuso).

#### `_components/shared/__tests__/resident-dependent-field.test.tsx`
- [ ] Seleciona dependente existente → callback recebe `{ resident_dependent_id }`.
- [ ] Seleciona "novo" + preenche name/phone → callback recebe `{ resident_dependent: {name, phone} }`.

#### Regressão do wizard de inquilino (G6)
- [ ] Atualizar/observar os testes de `tenants/_components/wizard` para que **não** existam mais `email`/`phone_alternate` (asserir ausência no submit/no DOM do contact step).

> Rodar (devem falhar / ou refletir remoção):
> ```bash
> npx vitest run "lib/utils/__tests__/lease-derivations.test.ts" "lib/utils/__tests__/date.test.ts" "app/(dashboard)/_components/shared/__tests__/resident-dependent-field.test.tsx"
> ```

### 2. GREEN — implementar utils, schema shape, componente, e remover campos fantasma; refatorar `lease-form-modal` p/ consumir os utils.

### 3. REFACTOR — DRY
- `lease-form-modal` **sem** lógica duplicada de derivação/parse/dependente (tudo importado).
- `calculateTagFee` continua a fonte única (helpers.ts) — só reusar.
- Nenhum re-export; consumidores importam da fonte.

### 4. VERIFY — gate (escopo desta sessão)
```bash
cd frontend
npx vitest run "lib/utils/__tests__/lease-derivations.test.ts" "lib/utils/__tests__/date.test.ts" \
  "app/(dashboard)/_components/shared/__tests__/resident-dependent-field.test.tsx" \
  "app/(dashboard)/tenants"   # regressão do wizard de inquilino (sem email/phone_alternate)
npm run type-check
npx eslint lib/utils/lease-derivations.ts lib/utils/date.ts lib/schemas/lease.schema.ts lib/schemas/tenant.schema.ts \
  "app/(dashboard)/_components/shared/resident-dependent-field.tsx" \
  "app/(dashboard)/leases/_components/lease-form-modal.tsx" "app/(dashboard)/tenants/_components/wizard"
```

---

## Constraints
- **Refator completo**: mover lógica e atualizar **todos** os consumidores; sem shim/re-export/duplicata. `lease-form-modal` mantém comportamento idêntico.
- **DRY**: wizard da S54 reusará estes utils/componente — não duplicar depois.
- **G6/D4**: remover `email`/`phone_alternate` da UI (não adicionar ao backend).
- Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção; sem barrel/re-export. Tipos estritos (`noUncheckedIndexedAccess`).
- `import type` para tipos; named exports.

## Critérios de Aceite (binários)
- [ ] `lease-derivations.ts` (rental/due_day) + `date.ts` (`parseLocalDate`) criados, testados, e **consumidos** pelo `lease-form-modal` (lógica inline removida; comportamento idêntico).
- [ ] `leaseValuesSchemaShape` exportado em `lease.schema.ts` e composto pelo `leaseSchema` (contrato público inalterado).
- [ ] `resident-dependent-field.tsx` reutilizável (existente ⊕ novo), sem `apiClient`/PATCH.
- [ ] `email`/`phone_alternate` removidos de `tenant.schema.ts`, `contact-info-step.tsx`, wizard (`index.tsx`/`types.ts`) e dos testes.
- [ ] `vitest` (arquivos tocados + `app/(dashboard)/tenants`) verde; `type-check` 0 erros; `eslint` 0 erros/0 warnings; sem suppressions.

## Handoff
1. Gate verde.
2. Atualizar `prompts/SESSION_STATE.md` (S53 concluída; arquivos; contratos abaixo p/ S54).
3. `/audit` contra os Critérios de Aceite.
4. Commit:
   ```
   refactor(frontend): extract lease derivations/date/resident-dependent utils + drop phantom email/phone_alternate

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima: **S54 — wizard de onboarding** (reusa estes utils/componente + o contrato da API da S52).

---

### Contratos cross-session (S54 consome verbatim)
- `@/lib/utils/lease-derivations` → `deriveRentalValue(apartment, numberOfTenants)`, `deriveDueDayFromStartDate(date)`.
- `@/lib/utils/date` → `parseLocalDate(s)`.
- `@/lib/utils/helpers` → `calculateTagFee(numberOfTenants)` (já existente).
- `@/lib/schemas/lease.schema` → `leaseValuesSchemaShape` (compor no schema combinado).
- `@/app/(dashboard)/_components/shared/resident-dependent-field` → produz `{resident_dependent_id}` ou `{resident_dependent:{name,phone}}` (alinhado ao body da S52).
- `email`/`phone_alternate` **não existem mais** no domínio do inquilino (não coletar no wizard).
