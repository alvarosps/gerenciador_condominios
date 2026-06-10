# Mobile — Fluxo "Novo inquilino + contrato" (Plano 2) — Design

> **Plano 2** da feature de onboarding. O **Plano 1 (web)** está em `docs/plans/2026-06-07-tenant-lease-onboarding-design.md` e foi implementado no branch `feat/tenant-lease-onboarding` (S51–S55). Este documento desenha a versão **mobile (app admin Expo)**, que **reusa o mesmo endpoint transacional** do backend.

**Goal:** Um fluxo guiado, admin-only, no app mobile que cria **inquilino (novo ou existente) + locação** em uma única chamada transacional (`POST /api/onboarding/tenant-lease/`), com passo final opcional de **gerar e compartilhar o PDF do contrato**. Espelha o wizard web em paridade de escopo.

**Architecture:** Wizard de 6 passos (estado em memória, uma rota) no grupo `(admin)` do Expo Router, consumindo o endpoint de onboarding via um novo hook TanStack Query. Substitui o atual `new-lease.tsx` (limitado) como único caminho de criação de locação no mobile. Camada de dados (schema Zod, validadores, derivações, utilitários de download) espelha 1:1 a do web.

**Tech Stack:** Expo SDK 54 · expo-router 6 (typed routes) · React 19 / React Native 0.81 · TanStack Query 5 · axios · zustand · zod 4 · react-native-paper 5 · expo-file-system + expo-sharing (PDF). Testes: **jest-expo + @testing-library/react-native** (novo harness no `mobile/`).

---

## 0. Pré-requisito de execução (BLOQUEANTE)

O endpoint `POST /api/onboarding/tenant-lease/` (e todo o wizard web S52–S55) **existe apenas no branch local `feat/tenant-lease-onboarding` (fe3fb5e)** — **não está no `master` nem no `origin`**. O `master` (PR #10) contém só o **S51** (root-fixes em `core/serializers.py`: validação de apto ocupado, captura/auditoria de dependentes, guard de locador) + os docs/prompts.

**Antes de executar este plano:**
1. Mergear + deployar o backend de onboarding (`feat/tenant-lease-onboarding` → `master` → produção), de modo que `POST /api/onboarding/tenant-lease/` exista no deploy. Sem isso, o app mobile não tem o que chamar.
2. O **código do wizard web** é usado apenas como **referência canônica** para espelhamento (lido de um worktree do branch); não é dependência de runtime do mobile.

O plano em si é desenhado **contra `master`** (base do branch mobile). Sugestão de branch: `feat/mobile-tenant-lease-onboarding` a partir de `master`.

---

## 1. Estado atual (o que já existe no mobile)

App Expo em `mobile/` (separado do frontend web). Convenções confirmadas por investigação profunda:

- **Navegação:** Expo Router; grupos `(admin)` e `(tenant)`. Admin é **Tabs**: Dashboard · Imóveis (`properties`) · Financeiro · Ações (`actions`) · Alertas. Cada tab tem stack próprio. Role binário por `is_staff`; `(admin)` protegido em `mobile/app/(admin)/_layout.tsx`.
- **API/auth:** `mobile/lib/api/client.ts` (axios, `API_BASE_URL = EXPO_PUBLIC_API_URL ?? http://localhost:8008/api`, interceptor com Bearer + refresh 401 + fila). `mobile/store/auth-store.ts` (zustand; `role = is_staff ? admin : tenant`). Tokens em `expo-secure-store`.
- **Hooks (TanStack Query):** queryKeys `["admin", ...]`; mutations com invalidação em `onSuccess`; `mobile/lib/api/hooks/use-admin-properties.ts` tem `useBuildings`, `useApartments`, `useLeases`, `useTenantSearch`, `useCreateLease`, `useGenerateContract`.
- **Formulários:** **sem react-hook-form**; `useState` por campo; validação manual → `Alert.alert`; **sem máscaras**; datas como texto `YYYY-MM-DD`; react-native-paper (`TextInput mode="outlined"`, `SegmentedButtons`, `Button`, `Switch`, `Menu`, `Checkbox`). Sem primitivo de wizard.
- **PDF/arquivos:** `mobile/app/(tenant)/contract.tsx` baixa via `FileSystem.downloadAsync(url, cacheDir, {headers:{Authorization:Bearer}})` → `Sharing.shareAsync(uri, {mimeType:'application/pdf'})`. Upload de comprovantes via `FormData` multipart.
- **Testes:** **inexistentes** no `mobile/` (só `tsconfig`/Expo). Alias `@/*` → raiz do `mobile/`.

### `new-lease.tsx` (a ser substituído)
`mobile/app/(admin)/properties/new-lease.tsx` hoje: busca **inquilino existente** (`/tenants/?search=`), escolhe apto vago, coleta `start_date`/`validity_months`/`rental_value`, **fixa `number_of_tenants=1`** e faz `POST /leases/` direto. **Não** cria inquilino, sem dependentes, sem 2 ocupantes, sem o endpoint transacional. É o ponto de substituição.

### Bug latente a corrigir
`useGenerateContract` (`use-admin-properties.ts:92`) tipa a resposta como `{contract_url}`, mas o backend retorna `{pdf_path}` (200) **ou** `{task_id,status}` (202). O botão "Gerar Contrato" em `[id].tsx` está, portanto, quebrado. Este plano corrige.

---

## 2. Decisões de produto (travadas)

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | `new-lease.tsx` | **Substituir** — onboarding vira o único caminho de criação de locação (DRY/SOLID; sem backwards-compat). |
| 2 | Escopo | **Espelhar o web** — novo/existente inquilino, 1–2 ocupantes, dependente residente (novo/existente), PDF opcional. |
| 3 | UI | **Wizard em passos** — estado em memória, uma rota, `Voltar`/`Próximo`, indicador de progresso, validação por passo. |
| 4 | PDF | **Gerar + compartilhar** — `generate_contract/` → 200 baixa+share, 202 mostra mensagem de processamento. |
| 5 | Testes | **Cobertura ampla** (utils + hooks + componentes) com **jest-expo + @testing-library/react-native**. |

---

## 3. Contrato da API (exato)

`POST /api/onboarding/tenant-lease/` · `IsAdminUser` · `@transaction.atomic` (`select_for_update` no apto + fallback `IntegrityError`) · **201 Created**.

### Request
```jsonc
{
  "tenant": {                      // sem "id" = cria; com "id" = atualiza existente (partial)
    "id"?: number,
    "name": string,                // min 3
    "cpf_cnpj": string,            // CPF (PF) | CNPJ (PJ), único
    "is_company": boolean,
    "phone": string,               // telefone BR válido
    "profession": string,          // min 3
    "marital_status": string,      // obrigatório se !is_company; ver enum
    "due_day": number,             // 1..31
    "rg"?: string | null,
    "furniture_ids"?: number[]
  },
  "lease": {                       // NÃO enviar responsible_tenant_id / tenant_ids (servidor injeta)
    "apartment_id": number,
    "number_of_tenants": 1 | 2,
    "start_date": "YYYY-MM-DD",
    "validity_months": number,     // 1..60
    "rental_value"?: number,       // derivado do apto se omitido
    "tag_fee"?: number,
    "deposit_amount"?: number | null,
    "cleaning_fee_paid"?: boolean,
    "tag_deposit_paid"?: boolean,
    "due_day": number,
    "prepaid_until"?: string | null,   // admin-only
    "is_salary_offset"?: boolean       // admin-only
  },
  // 2º morador (apenas se number_of_tenants == 2): UM dos dois, nunca ambos
  "resident_dependent"?: { "name": string, "phone": string, "cpf_cnpj"?: string },
  "resident_dependent_id"?: number
}
```

### Enum `marital_status`
`Solteiro(a)`, `Casado(a)`, `Divorciado(a)`, `Viúvo(a)`, `União Estável` (+ legados: `Solteiro`, `Casado`, `Divorciado`, `Viúvo`, `Separado`).

### Resposta 201
`{ "tenant": <TenantSerializer>, "lease": <LeaseSerializer> }` (objetos completos com nested `apartment`, `responsible_tenant`, `tenants`, `resident_dependent`, etc.).

### Erros 400 (namespaced)
- `{"tenant": {<campo>: [msg]}}` — ex.: `cpf_cnpj`, `phone`, `marital_status`, `due_day`, `id` (`"Inquilino não encontrado."`).
- `{"lease": {<campo>: [msg]}}` — ex.: `apartment_id` (`"Apartamento não encontrado."`), `apartment` (`"Este apartamento já possui um contrato ativo."`), `number_of_tenants` (`"Deve ser 1 ou 2."` / excede `max_tenants` / `"Para 2 inquilinos, o apartamento precisa ter valor de aluguel para 2 pessoas (rental_value_double) definido."`), `start_date`, `validity_months`, `rental_value`.
- `{"lease": {"resident_dependent": {<campo>: [msg]}}}` — dependente novo inválido.
- Top-level: XOR (`"Informe apenas um: 'resident_dependent' (novo) ou 'resident_dependent_id' (existente)."`); campos server-controlled enviados por engano.

---

## 4. Arquitetura mobile

Camadas seguem as convenções do app (hooks `apiClient` + queryKeys `["admin",...]`, Paper, `Alert`, sem RHF, datas texto). Mocks só de boundaries.

### Arquivos a criar
| Arquivo | Responsabilidade |
|---------|------------------|
| `mobile/lib/validators/brazilian.ts` | `validateCpfCnpj`, `validateBrazilianPhone` (porte mínimo dos validadores web; mobile é pacote separado). |
| `mobile/lib/schemas/tenant-lease-onboarding.ts` | Zod espelhando o schema web: campos tenant/lease, `refine` CPF/telefone, `superRefine` 2º morador (XOR + obrigatório quando 2 ocupantes). Tipo `TenantLeaseOnboardingFormValues`. |
| `mobile/lib/utils/lease-derivations.ts` | `deriveRentalValue(apt, n)` (2 → `rental_value_double ?? rental_value`), `deriveDueDayFromStartDate(date)` (dia do mês). |
| `mobile/lib/utils/date.ts` | `parseLocalDate(str)` (constrói `Date` em fuso local; evita off-by-one UTC−3). |
| `mobile/lib/utils/contract-download.ts` | `GenerateContractResult` (união), `isContractPdfResult`, `buildContractDownloadUrl(pdfPath)` (normaliza `\`→`/`; extrai segmento `contracts/`/`media/`; monta `${API_BASE_URL.replace(/\/api\/?$/,'')}/<rel>`), `PROCESSING_MESSAGE`. |
| `mobile/lib/api/hooks/use-admin-onboarding.ts` | `useOnboardTenantLease()` (POST `/onboarding/tenant-lease/`; invalida `["admin",{leases,apartments,tenants}]`) + `useOnboardingTenants()` (combina `useTenants`+`useLeases`; filtra inquilinos **sem locação ativa**) + `tenantToPrefill`. |
| `mobile/app/(admin)/properties/onboarding.tsx` | Wizard root (estado via `useReducer`; 6 passos + sucesso; aceita params `apartmentId`/`apartmentNumber` para pré-seleção). |
| `mobile/app/(admin)/properties/_components/types.ts` | Constantes de passo + `ERROR_FIELD_TO_STEP`. |
| `mobile/app/(admin)/properties/_components/step-start.tsx` | Passo 0 (novo/existente + seleção). |
| `mobile/app/(admin)/properties/_components/step-tenant-required.tsx` | Passo 1. |
| `mobile/app/(admin)/properties/_components/step-tenant-optional.tsx` | Passo 2 (dependentes + móveis). |
| `mobile/app/(admin)/properties/_components/step-lease-property.tsx` | Passo 3 (apto/ocupantes/2º morador/datas). |
| `mobile/app/(admin)/properties/_components/step-lease-values.tsx` | Passo 4 (valores/taxas). |
| `mobile/app/(admin)/properties/_components/step-review.tsx` | Passo 5 (resumo + criar). |
| `mobile/app/(admin)/properties/_components/success-step.tsx` | Passo final (gerar/baixar/compartilhar PDF). |
| `mobile/app/(admin)/properties/_components/resident-dependent-field.tsx` | Seletor 2º morador (existente OU novo); emite `{resident_dependent_id}` \| `{resident_dependent:{...}}`. |

### Arquivos a modificar
| Arquivo | Mudança |
|---------|---------|
| `mobile/lib/api/hooks/use-admin-properties.ts` | Corrige `useGenerateContract` → retorna `GenerateContractResult` (`{pdf_path}` \| `{task_id,status}`); remove o `{contract_url}`. Adiciona `useTenants()` (lista completa) se não existir. |
| `mobile/app/(admin)/properties/[id].tsx` | "Nova Locação" → push `onboarding` (com `apartmentId`/`apartmentNumber`); "Gerar Contrato" usa o fluxo de download+share corrigido. |
| `mobile/app/(admin)/properties/_layout.tsx` | Registra `onboarding`; remove `new-lease`. |
| `mobile/app/(admin)/index.tsx` | CTA "Novo inquilino + contrato" (card no topo, espelha `onboarding-cta` web). |

### Arquivos a remover
- `mobile/app/(admin)/properties/new-lease.tsx` (substituído).

---

## 5. Wizard — 6 passos + sucesso

Estado: `useReducer` único sobre `TenantLeaseOnboardingFormValues`. Validação por passo via Zod (valida o slice de campos do passo antes de `Próximo`). Header "Passo N de 6" + dots; `Voltar`/`Próximo`; `Criar` no passo 5.

| # | Passo | Campos / ação | Validação |
|---|-------|---------------|-----------|
| 0 | Início | `SegmentedButtons` **Novo** / **Existente**. Existente → lista (botões) de inquilinos **sem locação ativa** → `tenantToPrefill` preenche o form. | — |
| 1 | Inquilino — Dados | `name`, `is_company` (PF/PJ `SegmentedButtons`), `cpf_cnpj`, `phone`, `profession`, `marital_status` (`Menu`), `due_day`; `rg` (colapsável). | nome≥3, CPF/CNPJ, telefone, profissão≥3, estado civil, dia 1–31. |
| 2 | Inquilino — Opcionais | dependentes (lista add/remove: nome+telefone), móveis (`Checkbox` list → `furniture_ids`). | — |
| 3 | Contrato — Imóvel/Período | apartamento (lista de vagos via `useApartments` filtrando `!is_rented`), `number_of_tenants` (1/2 se `max_tenants≥2`), se 2 → `resident-dependent-field`, `start_date` (texto; auto-deriva `due_day` enquanto não editado), `validity_months`. | apto, 1–2, data, 1–60. |
| 4 | Contrato — Valores | `rental_value` (auto via `deriveRentalValue`), `tag_fee`, `due_day`; opcionais `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`; admin `is_salary_offset`, `prepaid_until`. | valores. |
| 5 | Revisão | resumo read-only → **Criar** (POST). | schema completo. |
| ✓ | Sucesso | check + nome do inquilino + apto; **Gerar contrato (PDF)** + **Concluir**. | — |

### Payload de submit (byte-for-byte com o web)
- `tenant`: inclui `id` só se existente; `dependents` filtra entradas sem nome/telefone; `furniture_ids` ?? [].
- `lease`: `start_date` formatada `yyyy-MM-dd`; `rental_value`/`tag_fee`/`deposit_amount` coeridos a número; `prepaid_until`/`is_salary_offset` só se admin.
- 2º morador: `resident_dependent` (novo) **ou** `resident_dependent_id` (existente), nunca ambos.

---

## 6. Seleção de inquilino existente

`useOnboardingTenants()` (espelha o web): `useTenants()` (lista completa) ∖ inquilinos presentes em **qualquer locação ativa** (`responsible_tenant.id` ou em `tenants[]`), via `useLeases()`. `tenantToPrefill(tenant)` mapeia para os valores do form, incluindo `furnitures → furniture_ids` (a API retorna `furnitures` nested; o form usa `furniture_ids`).

---

## 7. Passo PDF (gerar + compartilhar)

`useGenerateContract(leaseId)` → resposta `GenerateContractResult`:
- **200** (`isContractPdfResult`, `{pdf_path}`): `const url = buildContractDownloadUrl(pdf_path)` → `FileSystem.downloadAsync(url, ${cacheDir}contrato.pdf, {headers:{Authorization:Bearer <token>}})` → `Sharing.shareAsync(uri, {mimeType:'application/pdf', dialogTitle:'Contrato de Locação'})` (padrão de `(tenant)/contract.tsx`).
- **202** (`{task_id,status}`): exibe `PROCESSING_MESSAGE = "Contrato em processamento. Baixe em instantes na tela de Contratos."`.

URL: o web só **redireciona** para `${backend_sem_/api}/${pdf_path}` (arquivo servido pelo Django). O mobile monta a mesma URL absoluta e baixa direto com Bearer. (Mesmo comportamento/segurança do web atual.)

---

## 8. Erros → passo (`ERROR_FIELD_TO_STEP`)

Espelha o web:
- `tenant.*` → passo **1**.
- `lease.{apartment, apartment_id, number_of_tenants, start_date, validity_months, resident_dependent}` → passo **3**.
- `lease.{rental_value, tag_fee}` → passo **4**.

No 400: extrair o 1º erro namespaced (`tenant.*`/`lease.*`), `setStep(ERROR_FIELD_TO_STEP[campo])`, exibir a mensagem (PT) no campo (HelperText) e/ou `Alert`.

---

## 9. Decisões mobile-específicas

- **Estado:** `useReducer` único (não há RHF nas deps; mantém convenção do app).
- **Validação client:** espelha o web (CPF/telefone via Zod `refine`) com `mobile/lib/validators/brazilian.ts`; backend continua autoritativo (erros namespaced → passos).
- **Datas:** `TextInput` `YYYY-MM-DD` (sem DatePicker — convenção atual); `parseLocalDate` no parse.
- **Sem máscara** (convenção atual); formatação só na exibição.
- **Rota:** novo `onboarding.tsx`; `new-lease.tsx` removido; `[id].tsx` repointado; CTA no dashboard.

---

## 10. Estratégia de testes (jest-expo + @testing-library/react-native)

Novo harness no `mobile/`. **Mock apenas de boundaries externos** (módulos Expo nativos, HTTP, expo-router); nunca código interno do app.

- **Setup:** `jest-expo` preset, `@testing-library/react-native`, `@testing-library/jest-native` matchers; scripts `test`/`test:watch` no `mobile/package.json`; deps em `devDependencies`.
- **HTTP:** mock do boundary (MSW server em node, ou mock do `apiClient`/axios adapter) — não mockar hooks internos.
- **Boundaries Expo mockados:** `expo-file-system` (`downloadAsync`), `expo-sharing` (`shareAsync`, `isAvailableAsync`), `expo-secure-store`, `expo-router` (`useRouter`, `useLocalSearchParams`).
- **Cobertura:**
  - **Utils puros (TDD):** `lease-derivations`, `date`, `contract-download`, `validators/brazilian`, schema Zod (incl. `superRefine` XOR/obrigatório), `ERROR_FIELD_TO_STEP`.
  - **Hooks:** `useOnboardTenantLease` (payload exato + invalidação), `useOnboardingTenants` (filtro sem-locação-ativa + `tenantToPrefill`), `useGenerateContract` corrigido (200 vs 202).
  - **Componentes:** wizard (avanço/retrocesso, validação por passo, novo×existente, 1×2 ocupantes, 2º morador novo×existente), `success-step` (200 baixa+share, 202 mensagem), roteamento de erro 400 → passo correto, retry após erro.
- **Gate mobile:** `npx tsc --noEmit` (strict) + lint + `jest` (0 falhas/0 warnings). Sem `# noqa`/`@ts-ignore`/`eslint-disable`; sem `as`/`!` em produção (carve-out só em fixtures de teste, se necessário).

---

## 11. Índice de exemplares

**Mobile (master — copiar estrutura/convenção):**
- `mobile/app/(admin)/properties/new-lease.tsx` — form com seleção + busca + submit (estrutura a evoluir para o wizard).
- `mobile/app/(admin)/actions/mark-paid.tsx` — extração de erro do axios.
- `mobile/app/(admin)/actions/rent-adjustment.tsx` — `Switch` + confirmação.
- `mobile/app/(tenant)/contract.tsx` — `FileSystem.downloadAsync` + `Sharing.shareAsync`.
- `mobile/lib/api/hooks/use-admin-properties.ts` — padrão de hook query/mutation.
- `mobile/lib/api/client.ts` — `API_BASE_URL` + interceptor.
- `mobile/lib/schemas/admin.ts` — schemas Zod de resposta.

**Web (branch `feat/tenant-lease-onboarding`, via worktree — espelhar lógica):**
- `frontend/app/(dashboard)/_components/tenant-lease-onboarding/` — wizard (index + steps + `types.ts` `ERROR_FIELD_TO_STEP` + `use-onboarding-tenants.ts`).
- `frontend/lib/schemas/tenant-lease-onboarding.schema.ts` — schema Zod (fonte do espelho).
- `frontend/lib/api/hooks/use-onboarding.ts` — `useOnboardTenantLease` (payload).
- `frontend/lib/utils/{lease-derivations,date,contract-download}.ts` — utilitários.
- `frontend/app/(dashboard)/_components/{onboarding-cta,shared/resident-dependent-field}.tsx`.
- `frontend/lib/api/hooks/use-leases.ts` — `useGenerateContract` (união 200/202).

**Backend (master / branch):**
- `core/serializers.py` — `TenantLeaseOnboardingSerializer`, `TenantSerializer`, `LeaseSerializer` (constantes de erro).
- `core/services/tenant_onboarding_service.py`, `core/viewsets/onboarding_views.py`, `core/urls.py` (rota).

---

## 12. Fora de escopo

- Qualquer coisa em `finances/` (outra sessão ativa).
- Assinatura digital de contrato; edição de locação existente; gestão de inquilinos fora do onboarding.
- DatePicker nativo / máscaras (mantém convenção atual do mobile).
- Mudanças no backend (o endpoint já existe no branch; só precisa ser mergeado/deployado).

---

## 13. Pré-requisitos + quebra em sessões (prévia)

**Pré-requisito #1:** backend de onboarding mergeado+deployado (ver §0).

Quebra preliminar (detalhada na fase de writing-plans):
1. **S-A — Harness de teste + data layer:** setup jest-expo/RNTL; validators + schema + derivations + date + contract-download; `useOnboardTenantLease`/`useOnboardingTenants`/`useTenants`; fix `useGenerateContract`. TDD nos puros + hooks.
2. **S-B — Wizard UI:** `onboarding.tsx` + passos 0–5 + `resident-dependent-field` + `types.ts`; testes de componente (avanço/validação/novo×existente/2 ocupantes).
3. **S-C — PDF + integração:** `success-step` (gerar/baixar/compartilhar 200/202) + CTA no dashboard + repointar `[id].tsx` + remover `new-lease.tsx` + `_layout`; roteamento de erro 400→passo; e2e/polish.

---

## 14. Follow-ups em aberto

- **FU-1 (herdado do web):** `LeaseSerializer.validate` não *exige* `resident_dependent` quando `number_of_tenants==2` para chamadas diretas ao `LeaseViewSet` (o onboarding está protegido via Zod + service). Pré-existente; decisão do usuário endurecer ou não. Não afeta o mobile (que usa o endpoint de onboarding).
- **FU-2:** servir o PDF de contrato a admin é hoje um redirect para arquivo estático (`/contracts/...`) sem auth dedicada — comportamento herdado do web. Avaliar endpoint autenticado de download no futuro (fora de escopo).
