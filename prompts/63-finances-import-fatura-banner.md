# Sessão 63 — Frontend: import de fatura (PDF) no modal de contas + `IptuRiskBanner` + hooks `useParseInvoice`/`useUpdateBillWithLines`/`useIptuAlerts`

> **Feature**: Contas de serviço tipadas (água/luz/IPTU) + parser de fatura PDF + alerta de IPTU + modal responsivo — `docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
> **Sessões da feature**: 56 → 57 → 58 → 59 → 60 → 61 → **62** → **63** → 64
> Esta sessão é a **Fase 6b (frontend) — import de fatura + banner de risco de IPTU**. Sobre a base responsiva da S62 (`DialogBody`, modal de contas com campos/statement condicional), adiciona: (1) hooks `useParseInvoice` (multipart) + `useUpdateBillWithLines` em `use-bills.ts`; (2) botão **"Importar fatura (PDF)"** no bloco `{isAdmin && …}` da página de Contas, que ao parsear **abre o modal pré-preenchido** (reusando o shape `billToDefaults`) com campos de statement (água/luz) e a **linha de parcela embutida reconciliada (travada)**; (3) `water_statement`/`electricity_statement` aninhados/nulláveis no `bill.schema.ts`; (4) selects de conta com label desambiguado `name — tipo · external_identifier`; (5) `IptuRiskBanner` + hook `useIptuAlerts` (uncached, `refetchOnWindowFocus`) renderizado no **dashboard de finanças** e na **página de Contas**, agrupado por `(prédio, inscrição)`. **Sem backend novo** (endpoints `parse_invoice`/`update_with_lines`/`iptu_alerts` são S60/S61); **sem seed** (S64).

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §5.2 fluxo, §6 reconciliação passado/atual/futuro, §7 `update_with_lines` + nested statement no `bill.schema.ts`, §8 modal/import/`behavior`/desambiguação, §9.2 banner uncached + agrupamento por `(prédio, inscrição)`, §10.5 "Atrasados inclui IPTU = drill-down", §14 Fase 6, §15 permissões, Apêndice B "Fase 6")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Hooks de `Bill` (CRUD + ações + `invalidateBillCaches`)** | `frontend/lib/api/hooks/use-bills.ts:1-229` (`ENDPOINT` :9; `CreateBillWithLines`/`BillLineInput` :21-31; `invalidateBillCaches` :78-82; `useCreateBillWithLines` :84-93; `usePayBill` :168-210) | Base de `useParseInvoice`/`useUpdateBillWithLines`. Espelhar `apiClient.post`+`onSuccess: () => invalidateBillCaches(queryClient)`. Estender `BillLineInput`/`CreateBillWithLines` com `installment_id`/`statement` (design §7.4) |
| **Interceptor `{results,count}`** | `frontend/lib/api/client.ts:11-38` (default `'Content-Type': 'application/json'` :11-13; desempacota `'results' in data && 'count' in data` :24-35) | `parse_invoice` (objeto draft) e `iptu_alerts` (objeto plano `{alerts, warning_count, critical_count}`) **NÃO** têm shape `{results,count}` → não são desempacotados; travar por teste o objeto cru (design §8.2). **Multipart**: enviar `FormData` com `headers: { 'Content-Type': undefined }` (browser seta o boundary) |
| **Hook de banner uncached** | `frontend/lib/api/hooks/use-combined-calendar.ts:45` (`STALE_TIME` "uncached on the backend §11") + `useOverdueBills` :75-92 (`billSchema.parse`) | `useIptuAlerts` = leitura sensível a tempo → **`staleTime: 0` + `refetchOnWindowFocus: true`** (design §9.2). **Não** usar `staleTime` longo |
| **Componente banner (loading/erro/vazio/lista + `Alert`/`Badge`/ícone)** | `frontend/app/(dashboard)/financial/_components/overdue-alerts.tsx:1-113` (skeleton :11-21; erro :40-51; vazio :53-72; lista `AlertTriangle`/`Badge` :76-112) | Padrão do `IptuRiskBanner`. Status texto+ícone (não só cor); WARNING ≠ CRITICAL = 2 níveis (design §9.1) |
| **Modal de contas (`billToDefaults`, select `behavior`/conta recorrente, edit-locked)** | `frontend/app/(dashboard)/finances/bills/_components/bill-form-modal.tsx:53-88` (`emptyDefaults`/`billToDefaults`) + :116-117 (`behavior`) + :326-359 (select conta) + :362-382 (alertas) | **Ler a versão pós-S62** (responsivo + `external_identifier`/`issue_date`/statement condicional já lá). Esta sessão dispara a abertura via draft (reusa `billToDefaults`) e desambigua o select (design §8.2) |
| **Página de Contas (`{isAdmin && …}`)** | `frontend/app/(dashboard)/finances/bills/page.tsx:98-117` (bloco `{isAdmin && (<div className="flex flex-wrap gap-2">…)}`) + modais :164-174 | Site do botão "Importar fatura (PDF)" (junto a "Nova Conta") e do `<IptuRiskBanner />` (topo) |
| **Dashboard (onde o banner entra)** | `frontend/app/(dashboard)/page.tsx:27-54` (seções `FinanceKpiRow`/`RentCalendarSection`/`CombinedCalendarSection`) | `<IptuRiskBanner />` como seção, junto às KPIs do condomínio, acima do `CombinedCalendarSection` (design §9.2) |
| **`bill.schema.ts` (nested nullable)** | `frontend/lib/schemas/finances/bill.schema.ts:12-50` (`billLineItemSchema` :12-18; nested `nullable().optional()` :24-35; `line_items` default `[]` :38) | Aninhar `water_statement`/`electricity_statement` no mesmo padrão (design §7); round-trip do prefill no edit sem query-key novo |
| **`DialogBody` (S62)** | `frontend/components/ui/dialog.tsx` (S62: `DialogBody` `flex-1 overflow-y-auto`) | O modal usa o `DialogBody` da S62. **Não** recriar; consumir |
| **Teste de página admin/non-admin** | `frontend/app/(dashboard)/finances/bills/__tests__/bills-page.test.tsx:34-98` (`setBillsResponse`/`setAdmin`/non-admin esconde botões :69-79) | Espelho dos testes desta sessão. Reusar `setAdmin`/`setBillsResponse`/`createTestQueryClient` |
| **Teste de modal (mock dos hooks + captura de payload)** | `frontend/app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx:9-22` (`vi.mock(use-bills)` + stubs selects) + :115-126 (teste "Fase 3", reescrito na **S62**) | Mock de fronteira (hooks de mutação) + captura de payload. A reescrita do teste "Fase 3" é da S62; aqui foca import/banner/desambiguação |
| **Factories de mock** | `frontend/tests/mocks/data/finances.ts:44-106` (`createMockBillingAccount` :44-65 com `account_type`/`external_identifier` pós-S56; `createMockBill` :78-106) | Estender só se faltar campo (statement/account_type) — sem duplicar factory |
| **Mock policy (FE)** | `frontend/CLAUDE.md` + `.claude/rules/coding-standards.md` | HTTP via **MSW**; mockar só a fronteira (hooks de mutação no teste de página). **Nunca** mockar o componente sob teste nem o `apiClient` |

### O que as S56–S62 já entregaram (PRÉ-REQUISITO — NÃO recriar)

- **S56**: `BillingAccountType` (`water`/`electricity`/`iptu`/`internet`/`generic`, default `generic`) + `SupplyStatus` (`active`/`cut`) + campos `account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status` em `BillingAccount`; unique identity; `recurring_for_generation()` (exclui IPTU). **O serializer de `BillingAccount` expõe `account_type`/`external_identifier`/`secondary_identifier`** (a S56 atualizou `billing-account.schema.ts` com `account_type`/`holder_name`/`registered_address`/`secondary_identifier`/`supply_status`).
- **S57**: refactor `InstallmentPlan.linked_billing_account → billing_account` (BE+FE atômico). `installment-plan*.schema.ts`/`use-installment-plans.ts`/modal já renomeados.
- **S58**: `WaterBillStatement`/`ElectricityBillStatement` (1:1 `Bill`, readings-only) + `BillService.create_with_lines` estendido (statement + `BillLineItem.installment`) + `update_with_lines` (`@action(detail=True)`, só UNPAID+OPEN) + `BillSerializer` aninha `water_statement`/`electricity_statement` (nested nullable) + RLS.
- **S60**: `POST /api/finances/bills/parse_invoice` (MultiPartParser, is_staff) → draft `{bill, line_items, statement, matched_account, existing_bill_id, warnings}` (parse em memória, sem gravar). `bill.description` populado por `build_draft` (nome da conta casada, senão `"{tipo} {MM/YYYY}"`); cada `line_item` carrega `installment_id` (number|null) já reconciliado e `category_id` (number|null).
- **S61**: `IptuAlertService.evaluate(today_sp())` + `GET /api/finances/finance-dashboard/iptu_alerts` (UNCACHED, `FinancialReadOnly`) → linhas de risco por plano (WARNING/CRITICAL, `(prédio, inscrição)`, nº parcela + venc, deadline).
- **S62**: `DialogBody` (`flex-1 overflow-y-auto`) em `dialog.tsx`; `DialogContent` longo → `max-h-[90vh] flex flex-col`; modal de contas responsivo + campos `external_identifier`/`issue_date` + **bloco de statement condicional ao `account_type`** (água/luz) editável; reescrita do teste "Fase 3" → link Planos de Parcelamento; modais irmãos alinhados.

> **Se a S60/S61/S62 não estiverem concluídas, PARE.** Esta sessão depende delas (DEPENDENCY ORDER 60,61,62 → 63). Não recriar endpoints/`DialogBody`/campos de statement aqui.

---

## Escopo

### Arquivos a criar
- `frontend/lib/api/hooks/use-iptu-alerts.ts` — `useIptuAlerts()` (uncached / `staleTime: 0` / `refetchOnWindowFocus: true`) + tipos `IptuAlertLevel`/`IptuAlertRow`/`IptuAlertsResponse`.
- `frontend/lib/schemas/finances/invoice-parse.schema.ts` — schema do draft do `parse_invoice` (`parsedInvoiceSchema`: `bill` parcial (com `description`/`building_id`/`category_id`) + `line_items` (com `category_id`/`installment_id`) + `statement` (água/luz) + `matched_account` + `existing_bill_id` + `warnings`) e os tipos derivados. **Reusa** `billLineItemSchema`/`billingAccountSchema` (sem redefinir).
- `frontend/app/(dashboard)/finances/_components/iptu-risk-banner.tsx` — `IptuRiskBanner` (consome `useIptuAlerts`; lê `response.alerts` + `warning_count`/`critical_count`; agrupa por `(building_label, external_identifier)`; níveis WARNING/CRITICAL; vazio = null).
- `frontend/lib/api/hooks/__tests__/use-iptu-alerts.test.tsx` — testes do hook (MSW; shape cru sem desempacotar; `refetchOnWindowFocus`).
- `frontend/lib/api/hooks/__tests__/use-parse-invoice.test.tsx` — testes do `useParseInvoice`/`useUpdateBillWithLines` (MSW; `FormData`; header multipart; invalidação).
- `frontend/app/(dashboard)/finances/_components/__tests__/iptu-risk-banner.test.tsx` — testes do banner (warning/critical/vazio/agrupamento).
- `frontend/app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx` — testes do botão "Importar fatura" (admin vê / non-admin não vê; parse abre modal pré-preenchido) **e** do select desambiguado.

### Arquivos a modificar
- `frontend/lib/api/hooks/use-bills.ts` — **estender** `BillLineInput` com `installment_id?: number`; **estender** `CreateBillWithLines` com `statement?` (objeto tipado por água/luz) **e** novo tipo `UpdateBillWithLines` (`bill_id` + `bill` + `line_items` + `statement?`); adicionar `useParseInvoice()` (POST multipart → draft) + `useUpdateBillWithLines()` (`@action update_with_lines`, invalida caches). Imports/exports existentes intactos.
- `frontend/lib/schemas/finances/bill.schema.ts` — aninhar `water_statement`/`electricity_statement` (`nullable().optional()`) no `billSchema` (design §7) + os sub-schemas `waterStatementSchema`/`electricityStatementSchema`.
- `frontend/app/(dashboard)/finances/bills/page.tsx` — no bloco `{isAdmin && …}` (`:105-117`): botão **"Importar fatura (PDF)"** (`<input type="file" accept="application/pdf">` oculto + `useParseInvoice`); ao parsear, abrir o modal de contas pré-preenchido (passar o draft ao `BillFormModal`); montar `<IptuRiskBanner />` no topo.
- `frontend/app/(dashboard)/finances/bills/_components/bill-form-modal.tsx` — aceitar prop opcional `draft?: ParsedInvoice` (além de `bill`); quando `draft` vier, `form.reset(draftToDefaults(draft))` (reusa o shape de `billToDefaults`) — **prefill** dos campos do bloco de statement condicional (que a **S62 já renderiza**; aqui só preenche a partir de `draft.statement`) + **linha de parcela embutida reconciliada travada** (read-only); **selects de conta** (recorrente) renderizam label desambiguado `name — tipo · external_identifier`. **Não** recriar o bloco de statement (é da S62) nem quebrar o fluxo `bill`/create/edit existente.
- `frontend/app/(dashboard)/page.tsx` — montar `<IptuRiskBanner />` como seção do dashboard (junto às KPIs do condomínio, acima do `CombinedCalendarSection` — `:28-35`).
- `frontend/lib/api/query-keys.ts` — adicionar `finances.iptuAlerts` (`all` + `list`), espelhando `overdueBills` (`:176-180`).
- `frontend/tests/mocks/handlers.ts` — handlers MSW para `*/finances/bills/parse_invoice`, `*/finances/bills/:id/update_with_lines`, `*/finances/finance-dashboard/iptu_alerts` (se os testes precisarem de handlers globais; senão usar `server.use` por teste).
- `frontend/tests/mocks/data/finances.ts` — `createMockIptuAlertRow`/`createMockParsedInvoice` (factories de mock; estilo `createMockBill` `:78-106`) — só se necessário.

### NÃO fazer (pertence a outras sessões)
- **Nenhum backend** — `parse_invoice`/`update_with_lines`/`iptu_alerts`/`IptuAlertService`/parser são S58/S60/S61. Esta sessão **consome** os endpoints; **não** os cria/altera.
- **Nenhum seed** (`seed_condo_utilities`/dados reais) — é a **S64**.
- **Reescrever o teste "Fase 3" → link Planos de Parcelamento** — é a **S62** (design §8.2); se a S62 já fez, **não** mexer; se o teste ainda assertar "Fase 3", é resíduo da ordem — não regredir.
- **`DialogBody`/responsividade do modal/campos `external_identifier`/`issue_date`/bloco de statement condicional** — são da **S62**. Esta sessão **só** dispara a abertura pré-preenchida (via draft) e desambigua o select; **não** recria o layout.
- **Armazenamento do PDF** — proibido (design §4 decisão #4); o `FormData` é enviado e descartado pelo backend; o frontend **não** persiste o arquivo.
- **Parser de IPTU / OCR / multi-condomínio / fallback e-mail** — fora de escopo (design §16).

---

## Especificação

> Camadas (frontend, `.claude/rules/architecture.md` + `frontend/CLAUDE.md`): **Hooks** (`lib/api/hooks/`) toda comunicação via `apiClient` (TanStack Query); **Schemas** (`lib/schemas/finances/`) Zod; **Componentes** apresentacionais consomem hooks, sem `apiClient` direto. `import type` para tipos. Named exports. `@/` alias. Texto ao usuário em **PT**; identificadores/logs em **EN**. Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção (carve-out de fixture nos testes só quando inevitável, como em S33). Moeda via `formatCurrency` (`lib/utils/formatters.ts`); data DD/MM/YYYY (date-fns pt-BR). Erros via `getErrorMessage`/`handleError` (`lib/utils/error-handler.ts`).

### `frontend/lib/schemas/finances/invoice-parse.schema.ts` — draft do parser (design §5.2/§8.2)

Espelha o **draft serializado** que o `InvoiceDraftService.build_draft` (S60) devolve (NÃO o `ParsedLine` interno do parser S59); **não** desempacota `{results,count}` (objeto único — design §8.2); `statement` é `null` para `GENERIC`/IPTU. Reusa os schemas existentes (sem redefinir). A linha do draft já vem **reconciliada** pela S60: carrega `installment_id` (number|null, já resolvido) e `category_id` (number|null) — **nunca** `installment_number` (esse fica interno ao `ParsedLine` do parser S59, fora do draft serializado):
```ts
import { z } from 'zod';
import { billLineItemSchema, waterStatementSchema, electricityStatementSchema } from './bill.schema';
import { billingAccountSchema } from './billing-account.schema';

// Linha do draft serializado (S60) = BillLineItem com category_id + installment_id já resolvidos
// (NÃO installment_number — esse é interno ao ParsedLine do parser S59).
export const parsedLineSchema = billLineItemSchema.extend({
  category_id: z.number().nullable().optional(),
  installment_id: z.number().nullable().optional(),
});

export const parsedInvoiceSchema = z.object({
  bill: z.object({           // cabeçalho parcial que o admin confere antes de salvar
    competence_month: z.string(),
    due_date: z.string(),
    external_identifier: z.string().default(''),
    behavior: z.string(),    // "recurring" para consumo (§8.2)
    account_type: z.string().optional(),
    building_id: z.number().nullable().optional(),   // herdado da conta casada (S60)
    category_id: z.number().nullable().optional(),   // herdado da conta casada (S60)
    description: z.string(),  // S60 build_draft: nome da conta casada, senão "{tipo} {MM/YYYY}"
  }),
  line_items: z.array(parsedLineSchema),
  statement: z.union([waterStatementSchema, electricityStatementSchema]).nullable(),
  matched_account: billingAccountSchema.nullable(),
  existing_bill_id: z.number().nullable().optional(),   // idempotência → roteia para update_with_lines (S60)
  warnings: z.array(z.string()).default([]),
});

export type ParsedInvoice = z.infer<typeof parsedInvoiceSchema>;
export type ParsedLine = z.infer<typeof parsedLineSchema>;
```

### `frontend/lib/schemas/finances/bill.schema.ts` — statements aninhados (design §7)

```ts
// Readings-only; NENHUM campo de dinheiro (o dinheiro é BillLineItem — fonte única §3.2/§3.3).
export const waterStatementSchema = z.object({
  id: z.number().optional(),
  consumo_m3: z.number(),
  leitura_anterior: z.number().nullable().optional(),
  leitura_atual: z.number().nullable().optional(),
  leitura_dias: z.number().nullable().optional(),
  data_leitura: z.string().nullable().optional(),
  agua_status: z.enum(['active', 'cut']).default('active'),
  esgoto_status: z.enum(['active', 'cut']).default('active'),
});

export const electricityStatementSchema = z.object({
  id: z.number().optional(),
  consumo_kwh: z.number(),
  energia_injetada_kwh: z.number().nullable().optional(),
  leitura_anterior: z.number().nullable().optional(),
  leitura_atual: z.number().nullable().optional(),
  leitura_dias: z.number().nullable().optional(),
  classe: z.string().optional().default(''),
  bandeira: z.string().optional().default(''),
});
```
Adicionar ao `billSchema` (junto dos nested `:24-35`):
```ts
  water_statement: waterStatementSchema.nullable().optional(),
  electricity_statement: electricityStatementSchema.nullable().optional(),
```
E exportar os tipos `WaterStatement`/`ElectricityStatement`.

### `frontend/lib/api/hooks/use-bills.ts` — `useParseInvoice` + `useUpdateBillWithLines` (design §5.2/§7.4)

Estender os tipos:
```ts
export interface BillLineInput {
  description: string;
  amount: number;
  is_offset?: boolean;
  category_id?: number;
  installment_id?: number;          // NEW — vincula a linha ao Installment embutido (§7.1)
}

export type BillStatementInput =
  | { kind: 'water'; consumo_m3: number; /* …campos readings-only */ }
  | { kind: 'electricity'; consumo_kwh: number; /* … */ };
// (Modelar exatamente os campos que o backend create_with_lines/update_with_lines aceita —
//  ver finances/serializers.py da S58. Sem money fields.)

export interface CreateBillWithLines {
  bill: Record<string, unknown>;
  line_items: BillLineInput[];
  statement?: BillStatementInput | null;   // NEW (§7.1)
}

export interface UpdateBillWithLines {
  bill_id: number;
  bill?: Record<string, unknown>;
  line_items: BillLineInput[];
  statement?: BillStatementInput | null;
}
```

`useParseInvoice()`:
```ts
export function useParseInvoice() {
  return useMutation({
    mutationFn: async (file: File): Promise<ParsedInvoice> => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await apiClient.post<unknown>(`${ENDPOINT}parse_invoice/`, formData, {
        headers: { 'Content-Type': undefined },   // browser sets the multipart boundary (§8.2)
      });
      return parsedInvoiceSchema.parse(data);       // não é {results,count} → cru
    },
  });
}
```
- **Sem `onSuccess`/invalidação** — `parse_invoice` **não grava nada** (design §5.2): só retorna o draft que abre o modal. A gravação acontece quando o admin salva (via `create_with_lines`/`update_with_lines`).
- Erro (não-PDF/emissor desconhecido → 400/422 PT do backend) propaga ao caller, que usa `handleError`.

`useUpdateBillWithLines()`:
```ts
export function useUpdateBillWithLines() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateBillWithLines) => {
      const { data } = await apiClient.post<Bill>(
        `${ENDPOINT}${payload.bill_id}/update_with_lines/`,
        { bill: payload.bill, line_items: payload.line_items, statement: payload.statement ?? null },
      );
      return billSchema.parse(data);
    },
    onSuccess: () => invalidateBillCaches(queryClient),
  });
}
```
- `update_with_lines` substitui linhas + faz upsert da statement no **mesmo** `Bill`, **só** se UNPAID+OPEN (o backend rejeita pago/fechado com 400 PT — design §7.2); o erro propaga ao caller.
- `useCreateBillWithLines` (existente :84-93) **ganha** o campo `statement` no payload — sem mudar a assinatura pública (o tipo `CreateBillWithLines` já o carrega como opcional).

### `frontend/lib/api/hooks/use-iptu-alerts.ts` — banner uncached (design §9.2)

O endpoint `iptu_alerts` (S61) responde um **objeto plano** (NÃO lista nua, NÃO `{results,count}`): `{ alerts: IptuAlertRow[], warning_count: number, critical_count: number }`. O hook devolve **esse objeto inteiro** (o interceptor do `client.ts` não o desempacota — não é `{results}`). O zod `iptuAlertRowSchema` casa **exatamente** os campos do `IptuRiskRow` serializado pela S61.

```ts
export type IptuAlertLevel = 'warning' | 'critical';

export interface IptuAlertRow {
  plan_id: number;
  external_identifier: string;       // inscrição (billing_account.external_identifier)
  building_label: string;            // prédio (street_number) ou "Condomínio"
  level: IptuAlertLevel;
  overdue_count: number;
  deadline: string | null;           // due_date da 1ª parcela não-vencida (§9.1)
  overdue_due_dates: string[];       // vencimentos das parcelas em atraso (ISO)
  message: string;                   // PT, montada pelo IptuAlertService (§9.1)
}

export interface IptuAlertsResponse {
  alerts: IptuAlertRow[];
  warning_count: number;
  critical_count: number;
}

export function useIptuAlerts() {
  return useQuery({
    queryKey: queryKeys.finances.iptuAlerts.list(),
    queryFn: async (): Promise<IptuAlertsResponse> => {
      const { data } = await apiClient.get<IptuAlertsResponse>(
        '/finances/finance-dashboard/iptu_alerts/',
      );
      return data;   // objeto plano (não {results,count}) — interceptor não desempacota (§8.2)
    },
    staleTime: 0,                      // uncached: depende de today_sp() + estado de pagamento (§9.2)
    refetchOnWindowFocus: true,        // virada de meia-noite / pagamento reflete ao voltar à aba
  });
}
```
> Os campos são **exatamente** o `IptuRiskRow` que a S61 serializa: `plan_id`/`external_identifier`/`building_label`/`level`/`overdue_count`/`deadline`/`overdue_due_dates`/`message`. **Não** renomear para `inscription`/`building_id`/`building_name`/`terms` (shape antigo descartado) — usar os nomes canônicos da S61 verbatim.

### `IptuRiskBanner` (design §9.2 + §10.5)

- Consome `useIptuAlerts()`, lendo `response.alerts` (lista de `IptuAlertRow`) + `response.warning_count`/`response.critical_count`. **Loading** → skeleton (espelha `OverdueSkeleton` `:11-21`). **Erro** → card de erro PT. **Vazio (`response.alerts.length === 0`)** → **`return null`** (banner some quando não há risco; NÃO renderizar "tudo em dia" para não competir com o KPI de Atrasados — design §10.5).
- **Agrupamento por `(building_label, external_identifier)`** (design §9.2): agrupar as `IptuAlertRow` por `building_label`+`external_identifier`; cada grupo lista as parcelas vencidas (`overdue_due_dates`) com seus vencimentos; o nível do grupo = o pior (`critical` > `warning`). `warning_count`/`critical_count` do response alimentam o resumo/contadores do banner.
- **Níveis visuais** (status texto+ícone, nunca só cor): `warning` → `AlertTriangle`/âmbar (`text-amber-700 dark:text-amber-400`, `border-amber-500/30`); `critical` → `AlertTriangle`/`text-destructive`/`border-destructive/30`. Badge com `overdue_count`. Mensagem PT vinda do `message` da row (não reconstruir a frase no front — DRY com o serviço).
- **Schema zod** (`iptuAlertRowSchema`): casa `plan_id`/`external_identifier`/`building_label`/`level`/`overdue_count`/`deadline` (`nullable`)/`overdue_due_dates` (`array(string)`)/`message` — exatamente os nomes do `IptuRiskRow` da S61. O response inteiro = `{ alerts: iptuAlertRowSchema[], warning_count, critical_count }`.
- **Drill-down, não total** (design §10.5): copy curta deixa claro que é risco de perda do parcelamento, sem somar valores (o total devido já está no KPI Atrasados).
- Renderizado em **dois** lugares: dashboard (`app/(dashboard)/page.tsx`) e página de Contas (`bills/page.tsx`) — **mesmo** componente (DRY), cada um monta `<IptuRiskBanner />`.

### Botão "Importar fatura (PDF)" + abertura pré-preenchida (design §8.2)

Na página de Contas, dentro de `{isAdmin && (<div className="flex flex-wrap gap-2">…)}` (`:105-117`), ao lado de "Nova Conta":
- `<Button variant="outline">` com ícone (`FileUp` lucide) + label **"Importar fatura (PDF)"** que dispara um `<input type="file" accept="application/pdf" hidden ref>` (`.click()`).
- `onChange` → pega `file`, chama `useParseInvoice().mutate(file, { onSuccess: (draft) => setImportDraft(draft), onError: (e) => handleError(e, 'Não foi possível ler a fatura') })`.
- Estado `importDraft: ParsedInvoice | null`; ao setar, abrir `<BillFormModal open draft={importDraft} onClose={…} />` (reusa o modal; passa `draft` em vez de `bill`).
- O modal, com `draft`, faz `form.reset(draftToDefaults(draft))`:
  - cabeçalho (`competence_month`/`due_date`/`external_identifier`/`description`/`behavior=recurring`);
  - linhas (`line_items` → `{description, amount, is_offset, category_id, installment_id}`); a **linha de parcela embutida reconciliada** (com `installment_id` já resolvido pela S60) é renderizada **travada** (read-only / `disabled`) — o admin não edita a reconciliação (design §6 "atual: vincula"); as demais linhas editáveis;
  - bloco de statement (água/luz) preenchido a partir de `draft.statement` (a UI condicional ao `account_type` é da S62; aqui só prefill);
  - `warnings` do draft exibidos num `Alert` (ex.: "crie o parcelamento", "FATURA ARRECADADA", resíduo de soma — design §5.3/§5.4).
- Ao salvar, **rotear por `existing_bill_id`** (NÃO por `matched_account`): `draft.existing_bill_id` truthy → `useUpdateBillWithLines({ bill_id: existing_bill_id, bill, line_items, statement })` (substituição — design §5.5); senão → `useCreateBillWithLines({ bill, line_items, statement })` (cria novo). A decisão create-vs-update vem **inteiramente** do `existing_bill_id` que o backend (S60) já resolveu via idempotência; **não** inventar lógica de match no front.

### Select de conta desambiguado (design §8.2-desambiguação)

Onde os selects renderizam contas (no `bill-form-modal.tsx` select "Conta recorrente" `:346-352`), trocar o label de `account.name` para um helper puro:
```ts
function accountLabel(account: BillingAccount): string {
  const typeLabel = ACCOUNT_TYPE_LABELS[account.account_type] ?? '';
  const id = account.external_identifier || account.secondary_identifier || '';
  return [account.name, typeLabel && `— ${typeLabel}`, id && `· ${id}`].filter(Boolean).join(' ');
}
// → "Conta de Luz - 836 — Luz · 1.273.798.010-05"
```
`ACCOUNT_TYPE_LABELS: Record<BillingAccountType, string>` = fonte única (`water→Água`, `electricity→Luz`, `iptu→IPTU`, `internet→Internet`, `generic→Genérica`). Assim duas luzes do 836 / dois IPTU do 850 ficam distinguíveis. **Não** duplicar o mapa de labels (extrair p/ `billing-account.schema.ts` ou um util compartilhado).

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`frontend/CLAUDE.md` + `.claude/rules/coding-standards.md`): HTTP via **MSW**; testar o componente/hook real. Mockar **só** fronteiras (hooks de mutação no teste de página, quando isolar a UI; MSW para os hooks de fetch). **Nunca** mockar o componente sob teste nem o `apiClient`. `renderWithProviders`/`createTestQueryClient` de `@/tests/test-utils`. `setAdmin` via `useAuthStore.setState`.

### 1. RED — escrever os testes primeiro

#### `frontend/lib/api/hooks/__tests__/use-parse-invoice.test.tsx`
```ts
it('useParseInvoice posts FormData with a multipart Content-Type override and returns the parsed draft', async () => {})
// MSW handler em */finances/bills/parse_invoice captura o request: Content-Type começa com 'multipart/form-data'
// (boundary setado pelo browser/jsdom porque o hook passa headers {'Content-Type': undefined});
// o body é FormData com 'file'; o handler responde o draft {bill, line_items, statement, matched_account, existing_bill_id, warnings};
// o hook retorna parsedInvoiceSchema.parse(data) (objeto cru, NÃO desempacotado).

it('useParseInvoice does NOT invalidate caches (parse_invoice never writes)', async () => {})
// spy em queryClient.invalidateQueries → não chamado no sucesso (design §5.2).

it('useParseInvoice surfaces a 400/422 error to the caller (não-PDF / emissor desconhecido)', async () => {})
// handler 400 → mutation entra em isError; mensagem PT do backend acessível via error.

it('useUpdateBillWithLines posts to bills/{id}/update_with_lines and invalidates bill caches', async () => {})
// handler em */finances/bills/:id/update_with_lines ecoa um Bill; o hook parseia via billSchema;
// onSuccess invalida finances.bills.all + combinedCalendar.all + overdueBills.all (spy em invalidateQueries).

it('useCreateBillWithLines forwards the optional statement in the payload', async () => {})
// handler captura o body: contém { statement: {kind:'water', consumo_m3:...} } quando passado.
```

#### `frontend/lib/api/hooks/__tests__/use-iptu-alerts.test.tsx`
```ts
it('useIptuAlerts fetches iptu_alerts and returns the flat {alerts, warning_count, critical_count} object', async () => {})
// MSW responde o OBJETO PLANO { alerts: IptuAlertRow[], warning_count, critical_count };
// o hook retorna o objeto inteiro (não {results,count} → interceptor não desempacota).

it('useIptuAlerts is configured uncached (staleTime 0, refetchOnWindowFocus true)', async () => {})
// inspecionar a config: o observer/queryCache mostra staleTime 0 e refetchOnWindowFocus true
// (ler queryClient.getQueryDefaults / options do observer, sem mockar interno).

it('useIptuAlerts surfaces backend errors', async () => {})
// handler 500 → isError.
```

#### `frontend/app/(dashboard)/finances/_components/__tests__/iptu-risk-banner.test.tsx`
```ts
it('renders nothing when there are no alerts', async () => {})
// MSW responde { alerts: [], warning_count: 0, critical_count: 0 } → o banner retorna null
// (container vazio; nenhum texto de risco).

it('renders a WARNING group with the building_label, external_identifier and overdue due dates', async () => {})
// 1 IptuAlertRow level='warning' → vê o external_identifier, "1 parcela atrasada", o venc (overdue_due_dates),
// ícone AlertTriangle âmbar.

it('renders a CRITICAL group when overdue_count >= 2 (distinct visual from warning)', async () => {})
// level='critical' → estilo destructive; copy de risco de parcelamento; NÃO mostra "pague até X".

it('groups multiple rows by (building_label, external_identifier) and shows the worst level per group', async () => {})
// 2 rows mesma (building_label, external_identifier) uma warning uma critical → 1 grupo, nível critical,
// ambas as parcelas vencidas listadas.

it('does not render a money total (drill-down, not a second Atrasados total)', async () => {})
// nenhum formatCurrency/valor R$ no banner (design §10.5).
```

#### `frontend/app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx`
```ts
it('hides "Importar fatura" and "Nova Conta" for non-admin users', async () => {})
// setAdmin(false) → queryByRole button /importar fatura/i e /nova conta/i ausentes (espelha bills-page.test.tsx:69-79).

it('shows "Importar fatura" for admin users', async () => {})
// setAdmin(true) → ambos os botões presentes.

it('parsing a PDF opens the bill modal prefilled from the draft (header + lines + locked installment line)', async () => {})
// setAdmin(true); mock de useParseInvoice (fronteira) retornando um draft com 1 linha de consumo + 1 linha de
// parcela embutida reconciliada (installment_id=42, já resolvido pela S60); simular upload (fireEvent.change no input file);
// o modal abre com a descrição/competência/venc do draft; a linha com installment_id aparece travada (input disabled);
// a statement (consumo_m3) pré-preenchida.

it('renders two same-type accounts with distinct disambiguated labels "name — tipo · external_identifier"', async () => {})
// dois createMockBillingAccount account_type='electricity' com external_identifier distintos → no select de
// conta recorrente, dois options com labels diferentes (ambos contêm "— Luz ·" + o identificador respectivo).

it('saves via update_with_lines when the draft carries existing_bill_id (routes on existing_bill_id, not matched_account)', async () => {})
// draft com existing_bill_id=7 → salvar chama useUpdateBillWithLines({ bill_id: 7, ... }); useCreateBillWithLines NÃO chamado.

it('saves via create_with_lines when existing_bill_id is null (even with a matched_account)', async () => {})
// draft com matched_account preenchido mas existing_bill_id=null → salvar chama useCreateBillWithLines; useUpdateBillWithLines NÃO chamado.
```

> **`accountLabel` puro** — se ficar conveniente, extrair um teste unitário pequeno do helper (label correto p/ água/luz/IPTU; fallback a `secondary_identifier`; sem identificador → só `name — tipo`). Pode viver no `bills-page-import.test.tsx` ou num `__tests__/account-label.test.ts` se o helper for movido p/ util.

> Rodar (devem **falhar** — hooks/schema/banner/botão ainda não existem):
> ```bash
> cd frontend
> npx vitest run "lib/api/hooks/__tests__/use-parse-invoice.test.tsx" \
>   "lib/api/hooks/__tests__/use-iptu-alerts.test.tsx" \
>   "app/(dashboard)/finances/_components/__tests__/iptu-risk-banner.test.tsx" \
>   "app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx"
> ```

### 2. GREEN — implementar

1. `bill.schema.ts` — `waterStatementSchema`/`electricityStatementSchema` + aninhar no `billSchema` + tipos.
2. `invoice-parse.schema.ts` — `parsedInvoiceSchema`/`parsedLineSchema` reusando os schemas do passo 1.
3. `query-keys.ts` — `finances.iptuAlerts` (`all`/`list`).
4. `use-iptu-alerts.ts` — `useIptuAlerts` (uncached) + tipos.
5. `use-bills.ts` — `BillLineInput.installment_id`, `CreateBillWithLines.statement`, `UpdateBillWithLines`, `useParseInvoice` (multipart, sem invalidação), `useUpdateBillWithLines` (invalida); `useCreateBillWithLines` propaga `statement`.
6. `iptu-risk-banner.tsx` — banner (estados + leitura de `response.alerts`/`warning_count`/`critical_count` + agrupamento `(building_label, external_identifier)` + níveis warning/critical, vazio = null).
7. `bill-form-modal.tsx` — prop `draft?`, `draftToDefaults`, linha de parcela travada, prefill de statement, `accountLabel` desambiguado.
8. `bills/page.tsx` — botão "Importar fatura (PDF)" + input file + `importDraft` + `<IptuRiskBanner />` no topo.
9. `app/(dashboard)/page.tsx` — `<IptuRiskBanner />` como seção do dashboard.
10. `tests/mocks/handlers.ts` / `tests/mocks/data/finances.ts` — handlers/factories se os testes precisarem.

Rodar até verde:
```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-parse-invoice.test.tsx" "lib/api/hooks/__tests__/use-iptu-alerts.test.tsx" \
  "app/(dashboard)/finances/_components/__tests__/iptu-risk-banner.test.tsx" \
  "app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- `accountLabel`/`ACCOUNT_TYPE_LABELS` = **fonte única** (extrair p/ `billing-account.schema.ts` ou um util); o modal e qualquer select de conta usam o mesmo helper (DRY — design §8.2).
- `draftToDefaults` reusa o **mesmo shape** de `billToDefaults` (não duplicar o mapeamento de linhas — extrair o map de linhas se ficar repetido).
- O `IptuRiskBanner` agrupa via uma função pura `groupByBuildingInscription(rows)` testável; o nível do grupo via `worstLevel(rows)` (`critical` > `warning`). Mensagem PT vem do `row.message` (não reconstruir).
- `invalidateBillCaches` (existente) é a **única** fonte da invalidação de bills; `useUpdateBillWithLines` chama-a (não repete os 3 `invalidateQueries`).
- Sem `staleTime` longo no `useIptuAlerts` (uncached é a intenção — design §9.2); comentário curto cita o porquê.

### 4. VERIFY — gate (escopo desta sessão)

```bash
cd frontend
npx vitest run "lib/api/hooks/__tests__/use-parse-invoice.test.tsx" "lib/api/hooks/__tests__/use-iptu-alerts.test.tsx" \
  "app/(dashboard)/finances/_components/__tests__/iptu-risk-banner.test.tsx" \
  "app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx"
npm run lint
npm run type-check
npm run test:unit
```

> **Regressão obrigatória** (não quebrar os irmãos): rodar os testes existentes do modal/página de contas e do dashboard de finanças que tocam os mesmos arquivos:
> ```bash
> cd frontend
> npx vitest run "app/(dashboard)/finances/bills" "app/(dashboard)/_components/finance-calendar"
> ```
> O teste "Fase 3" do `bill-form-modal.test.tsx` (reescrito na S62) deve seguir verde — esta sessão **não** o altera.

---

## Constraints

- **Camadas FE** (`frontend/CLAUDE.md`): comunicação só via `apiClient` em hooks (`lib/api/hooks/`); componentes apresentacionais consomem hooks, **sem** `apiClient`/`axios`/`fetch` direto. Schemas Zod em `lib/schemas/`. Mutations invalidam queries no sucesso (`update_with_lines` sim; `parse_invoice` **não** — não grava).
- **Multipart**: `useParseInvoice` envia `FormData` com `headers: { 'Content-Type': undefined }` (browser seta o boundary). **Não** setar manualmente `multipart/form-data` (perde o boundary).
- **Sem desempacotar `{results,count}`**: `parse_invoice` (objeto draft) e `iptu_alerts` (objeto plano `{alerts, warning_count, critical_count}`) não têm esse shape → o interceptor (`client.ts:19-38`) não os toca; o hook recebe o cru (travar por teste — design §8.2).
- **`useIptuAlerts` uncached**: `staleTime: 0` + `refetchOnWindowFocus: true`; **proibido** `staleTime` longo (sensível a tempo/estado — design §9.2).
- **Banner = drill-down, não total** (design §10.5): vazio → `null`; **sem** somar valores R$ (o KPI Atrasados é o total). WARNING ≠ CRITICAL (estilo + copy distintos). Status nunca só por cor (texto + ícone).
- **Statements readings-only** (design §3.2/§3.3): `water_statement`/`electricity_statement` **sem** campos de dinheiro (o dinheiro é `BillLineItem`). Não inferir total a partir da statement.
- **Linha de parcela reconciliada travada** (design §6): a linha com `installment_id` (já resolvido pela S60 no draft serializado) é read-only no modal (a reconciliação vem do parser; o admin não a edita). As demais linhas editáveis. (`installment_number` é interno ao parser S59 — **não** está no draft serializado.)
- **Roteamento de save por `existing_bill_id`** (design §5.5): `draft.existing_bill_id` truthy → `useUpdateBillWithLines`; senão → `useCreateBillWithLines`. **Nunca** rotear por `matched_account`.
- **Desambiguação DRY** (design §8.2): `accountLabel`/`ACCOUNT_TYPE_LABELS` em **uma** fonte; todos os selects de conta usam o mesmo helper.
- **Sem backend / seed / DialogBody / responsividade / reescrita do teste Fase 3** — pertencem a S58/S60/S61/S62/S64. Esta sessão **só** consome.
- **Sem armazenar o PDF** (design #4): o `File` é enviado e descartado; o front não persiste.
- **Sem suppressions**: proibido `eslint-disable`/`@ts-ignore`/`@ts-expect-error`/`# noqa`. Corrigir o código. Sem `as`/`!` em produção (carve-out de fixture só nos testes, restrito ao boundary, como em S33). `import type` para tipos. Named exports; sem re-export/barrel novo.
- Texto ao usuário em **Português**; identificadores/logs/enum values em **Inglês**. Moeda via `formatCurrency`; data DD/MM/YYYY (date-fns pt-BR); erros via `getErrorMessage`/`handleError`.

## Critérios de Aceite (binários)

- [ ] `bill.schema.ts` aninha `water_statement`/`electricity_statement` (`nullable().optional()`, readings-only, sem dinheiro) + exporta `WaterStatement`/`ElectricityStatement`; nested existentes intactos.
- [ ] `invoice-parse.schema.ts` define `parsedInvoiceSchema`/`parsedLineSchema` reusando `billLineItemSchema`/`billingAccountSchema`/statements (sem redefinir); `parsedLineSchema` usa `category_id` + `installment_id` (number|null, override do `billLineItemSchema`), **nunca** `installment_number`; `bill` inclui `description` (string) + `building_id`/`category_id` (herdados da conta casada, S60); `existing_bill_id` (`z.number().nullable().optional()`); `statement` nullable; `warnings` lista; tipos exportados.
- [ ] `use-bills.ts`: `BillLineInput.installment_id?`, `CreateBillWithLines.statement?`, `UpdateBillWithLines`; `useParseInvoice` (FormData + `headers {'Content-Type': undefined}` + parse cru + **sem** invalidação); `useUpdateBillWithLines` (POST `bills/{id}/update_with_lines/` + `billSchema.parse` + `invalidateBillCaches`); `useCreateBillWithLines` propaga `statement`; exports/optimistic existentes intactos.
- [ ] `use-iptu-alerts.ts`: `useIptuAlerts` GET `finance-dashboard/iptu_alerts/`, retorno objeto plano `{alerts, warning_count, critical_count}`, `staleTime: 0`, `refetchOnWindowFocus: true`; tipos `IptuAlertRow` (`plan_id`/`external_identifier`/`building_label`/`level`/`overdue_count`/`deadline`/`overdue_due_dates`/`message`)/`IptuAlertsResponse`/`IptuAlertLevel`; `query-keys.ts` ganha `finances.iptuAlerts`.
- [ ] `IptuRiskBanner`: estados loading/erro; vazio (`response.alerts.length === 0`) → `null`; agrupa por `(building_label, external_identifier)`; warning vs critical visualmente distintos (texto+ícone, não só cor); badge `overdue_count`; mensagem PT do `row.message`; **sem** total R$ (drill-down). Renderizado no dashboard (`app/(dashboard)/page.tsx`) **e** na página de Contas.
- [ ] Botão "Importar fatura (PDF)" no bloco `{isAdmin && …}` da página de Contas (não-admin **não** vê); upload chama `useParseInvoice`; sucesso abre `BillFormModal` pré-preenchido (cabeçalho + linhas + **linha de parcela embutida travada via `installment_id`** + statement) com `warnings` exibidos; PDF não persistido. Salvar **roteia por `existing_bill_id`** (truthy → `useUpdateBillWithLines({ bill_id, ... })`; senão → `useCreateBillWithLines`), **não** por `matched_account`.
- [ ] Selects de conta renderizam label desambiguado `name — tipo · external_identifier` (fallback `secondary_identifier`); duas contas do mesmo tipo → labels distintos; `ACCOUNT_TYPE_LABELS`/`accountLabel` fonte única (DRY).
- [ ] Testes Vitest cobrem: parse FormData/multipart-header/cru/sem-invalidação/erro; update_with_lines invalida; create propaga statement; iptu_alerts objeto-plano/uncached/erro; banner warning/critical/vazio/agrupamento/sem-total; página non-admin não vê "Importar fatura" nem "Nova Conta", admin vê; parse abre modal pré-preenchido com linha travada; save roteia por `existing_bill_id` (update vs create); dois selects desambiguados. (Apêndice B "Fase 6".)
- [ ] `cd frontend && npm run lint && npm run type-check && npm run test:unit` — **zero erros e zero warnings**; **sem** `eslint-disable`/`@ts-ignore`/`@ts-expect-error`; **sem** `as`/`!` em produção (carve-out só em fixture de teste, restrito ao boundary); **sem** re-export/barrel novo. Regressão dos irmãos (`finances/bills`, `_components/finance-calendar`) verde; teste "Fase 3" (S62) intacto.
- [ ] Nenhum backend/endpoint/seed/`DialogBody`/responsividade do modal alterado; PDF não armazenado; `iptu_alerts`/`parse_invoice` consumidos sem desempacotar `{results,count}`.

## Handoff

1. Rodar e confirmar verde (gate, escopo desta sessão):
   ```bash
   cd frontend
   npx vitest run "lib/api/hooks/__tests__/use-parse-invoice.test.tsx" "lib/api/hooks/__tests__/use-iptu-alerts.test.tsx" \
     "app/(dashboard)/finances/_components/__tests__/iptu-risk-banner.test.tsx" \
     "app/(dashboard)/finances/bills/__tests__/bills-page-import.test.tsx"
   npx vitest run "app/(dashboard)/finances/bills" "app/(dashboard)/_components/finance-calendar"   # regressão irmãos
   npm run lint
   npm run type-check
   npm run test:unit
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`):
   - Linha da Sessão 63 (status **concluída**) na tabela da feature "Contas de serviço tipadas".
   - **Arquivos Criados**: `frontend/lib/api/hooks/use-iptu-alerts.ts`, `frontend/lib/schemas/finances/invoice-parse.schema.ts`, `frontend/app/(dashboard)/finances/_components/iptu-risk-banner.tsx`, + os 4 arquivos de teste.
   - **Arquivos Modificados**: `use-bills.ts` (`useParseInvoice`/`useUpdateBillWithLines` + `installment_id`/`statement`), `bill.schema.ts` (statements aninhados), `bills/page.tsx` (botão Importar + banner), `bill-form-modal.tsx` (prop `draft` + linha travada + `accountLabel`), `app/(dashboard)/page.tsx` (banner), `query-keys.ts` (`iptuAlerts`), `tests/mocks/handlers.ts`/`data/finances.ts` (se tocados).
   - **Nota**: "Fase 6b FE — import de fatura: `useParseInvoice` (multipart, sem gravar) abre o modal pré-preenchido (draft serializado da S60: `bill.description`/`building_id`/`category_id`, linhas com `category_id`+`installment_id`, linha de parcela embutida travada, statement prefill, `existing_bill_id`, warnings); save roteia por `existing_bill_id` (`useUpdateBillWithLines` substituição UNPAID+OPEN, senão `useCreateBillWithLines`); statements aninhados nullable no `bill.schema.ts`; selects de conta desambiguados `name — tipo · external_identifier`; `IptuRiskBanner` (uncached/`refetchOnWindowFocus`, response plano `{alerts, warning_count, critical_count}`, agrupado por `(building_label, external_identifier)`, drill-down sem total) no dashboard + página de Contas. **Sem backend/seed (S58/S60/S61/S64); `DialogBody`/responsividade/bloco de statement/reescrita teste Fase 3 = S62.**"
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir do branch da feature):
   ```
   feat(finances): complete session 63 — import de fatura no modal de contas + IptuRiskBanner + hooks parse/update/iptu-alerts

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **64 — Seed dos dados reais** (`scripts/data/condo_utilities_seed.json` + `seed_condo_utilities`, local → prod) — consome os modelos/serviços/endpoints/UI das S56–S63.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`bill.schema.ts`**: `billSchema` aninha `water_statement` (`waterStatementSchema` — `consumo_m3`/`leitura_*`/`data_leitura`/`agua_status`/`esgoto_status`, sem dinheiro) e `electricity_statement` (`electricityStatementSchema` — `consumo_kwh`/`energia_injetada_kwh`/`leitura_*`/`classe`/`bandeira`), ambos `nullable().optional()`. **S64** (seed) e o `BillSerializer` (S58) devem casar estes nomes.
- **`use-bills.ts`**: `useParseInvoice(): UseMutationResult<ParsedInvoice, …, File>` (POST `bills/parse_invoice/` multipart, `headers {'Content-Type': undefined}`, **sem** invalidação); `useUpdateBillWithLines()` (POST `bills/{id}/update_with_lines/`, invalida `bills`/`combinedCalendar`/`overdueBills`); `CreateBillWithLines.statement?: BillStatementInput | null`; `BillLineInput.installment_id?: number`. O payload de `statement` casa o que o `create_with_lines`/`update_with_lines` (S58) aceita (readings-only, sem dinheiro).
- **`use-iptu-alerts.ts`**: `useIptuAlerts(): UseQueryResult<IptuAlertsResponse>` (GET `finance-dashboard/iptu_alerts/`, **objeto plano**, `staleTime: 0`, `refetchOnWindowFocus: true`). `IptuAlertsResponse = { alerts: IptuAlertRow[], warning_count: number, critical_count: number }`; `IptuAlertRow = { plan_id, external_identifier, building_label, level: 'warning'|'critical', overdue_count, deadline: string|null, overdue_due_dates: string[], message }`. **Estes nomes são os do `IptuRiskRow` serializado pela S61 (CANON) — consumir verbatim, sem renomear.**
- **`IptuRiskBanner`** (`finances/_components/iptu-risk-banner.tsx`): lê `response.alerts` + `warning_count`/`critical_count`; agrupa por `(building_label, external_identifier)`, nível = pior do grupo, vazio → `null`, **sem** total R$ (drill-down do KPI Atrasados — design §10.5). Renderizado no dashboard (`app/(dashboard)/page.tsx`) e na página de Contas.
- **`accountLabel`/`ACCOUNT_TYPE_LABELS`** (fonte única — `billing-account.schema.ts` ou util compartilhado): label de select `name — tipo · external_identifier` (fallback `secondary_identifier`). Reusado por qualquer select de `BillingAccount` (modal de contas, futuros consumidores).
