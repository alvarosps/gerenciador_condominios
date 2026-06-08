# Sessão 62 — Frontend: `DialogBody` reutilizável + modal "Nova Conta" responsivo (header/footer fixos) + campos Inscrição/Emissão + link Planos de Parcelamento + alinhar modais irmãos do `finances`

> **Feature**: Contas de utilidade do condomínio + parser de fatura + alerta de IPTU — `docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
> **Sessões da feature**: 56 → 57 → 58 → 59 → 60 → 61 → **62** → 63 → 64
> Esta é a **Fase 6a (Frontend, layout)**: corrigir a causa-raiz do footer rolando junto com o corpo do modal (footer dentro da área `overflow-y-auto`) introduzindo um **`DialogBody`** (`flex-1 overflow-y-auto`) em `components/ui/dialog.tsx` e migrando os `DialogContent` longos para `max-h-[90vh] flex flex-col` (**header fixo, corpo rola, footer fixo** — padrão que já existe no `contract-view-modal`). Reestruturar `bill-form-modal.tsx` em blocos (header/corpo/footer), **renderizar os inputs `external_identifier` (Inscrição/UC) e `issue_date` (Emissão)** — que **já estão no schema e no payload** (UI-only), **renderizar o bloco de statement condicional ao `account_type`** (água → consumo/leituras/status; luz → consumo/injeção/leituras/classe/bandeira; oculto para IPTU/genérica) com inputs editáveis, trocar o alerta "Fase 3" por um **link para Planos de Parcelamento** e **reescrever** o teste `bill-form-modal.test.tsx:115-126` (assertar o link, não deletar), e **alinhar os modais irmãos novos do `finances`** (`employee`, `installment-plan`, `income-entry`) ao padrão `DialogBody`. 100% responsivo (1 col mobile / 2 col `sm+`, `w-[calc(100vw-2rem)]`, footer sempre visível). **Sem `useParseInvoice`/botão "Importar fatura"/`IptuRiskBanner` (S63); o prefill do statement a partir do draft do parser é S63; sem backend.**

---

## Contexto

Ler antes de escrever qualquer código:

- **Design doc (ler §8 "Modal Nova Conta responsivo + import de fatura" — §8.1 layout, §8.2 campos/blocos; §14 Fase 6; Apêndice B "Fase 6")**: `@docs/plans/2026-06-08-condo-utility-bills-parser-iptu-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado das sessões** (somente leitura — o orquestrador atualiza ROADMAP/SESSION_STATE): `@prompts/SESSION_STATE.md`
- **Regras do projeto**: `CLAUDE.md`, `frontend/CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`

### Exemplares (arquivo:linha — ler antes de codar)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **`DialogContent` longo `flex flex-col` + corpo `flex-1 overflow-y-auto`** (já existe, NÃO recriar — generalizar) | `frontend/app/(dashboard)/tenants/_components/contract-view-modal.tsx:72` (`DialogContent className="max-w-4xl max-h-[90vh] flex flex-col"`) + `:79` (corpo `flex-1 ... overflow-hidden`) | **Padrão-alvo** que esta sessão extrai para `DialogBody`. O `contract-view-modal` faz isso à mão; o objetivo é uma primitiva reutilizável. **Não** tocar o `contract-view-modal` (legado fora de escopo §8.1) |
| **Primitivas do Dialog (forwardRef + `displayName` + `cn(...)`)** | `frontend/components/ui/dialog.tsx:32-54` (`DialogContent`), `:56-68` (`DialogHeader`), `:70-82` (`DialogFooter`) | `DialogBody` espelha **exatamente** a forma de `DialogHeader`/`DialogFooter` (componente funcional `({className, ...props}) => <div className={cn(..., className)} {...props} />` + `displayName`) + entra no `export {...}` :111-122 |
| **Modal de conta atual (reestruturar — header/corpo/footer)** | `frontend/app/(dashboard)/finances/bills/_components/bill-form-modal.tsx` (DialogContent :190; grid 1/2 col :197; alerta "Fase 3" :362-370; alerta edit-locked :372-379; footer :398-408) | **Alvo principal**: corpo (`Form`) vai dentro do `DialogBody`; footer fica **irmão** do `DialogBody` (fora do scroll). `external_identifier`/`issue_date` já no `emptyDefaults`/`billToDefaults`/payload (:53-88, :157-174) — só **renderizar** os inputs. Trocar o alerta `isInstallment` (:362-370) por link a Planos de Parcelamento |
| **Teste do modal de conta (reescrever 115-126, não deletar)** | `frontend/app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx:115-126` (`blocks installment behavior with a Portuguese Phase 3 note`) | A asserção `findByText(/Fase 3/i)` (:123) vira **assertar o link "Planos de Parcelamento"** (`role="link"`, `href={ROUTES.FINANCES_INSTALLMENT_PLANS}`). Mantém a verificação de que `isInstallment` **bloqueia** o submit (`creates.toHaveLength(0)`) |
| **Modais irmãos a alinhar (mesmo DialogContent `max-h-[90vh] ... overflow-y-auto`)** | `employees/_components/employee-form-modal.tsx:146`; `installment-plans/_components/installment-plan-form-modal.tsx:156`; `income-entries/_components/income-entry-form-modal.tsx:147` (`max-w-lg`, **sem** max-h/flex) | Migrar os 3 para `max-h-[90vh] flex flex-col` + `DialogBody` (corpo = `Form`, footer irmão). Os testes deles **assertam labels/roles/testids, não DOM nesting** → não quebram (design §8.1 confirmado) |
| **Rota Planos de Parcelamento (constante única)** | `frontend/lib/utils/constants.ts:76` (`FINANCES_INSTALLMENT_PLANS: '/finances/installment-plans'`) | O link usa `ROUTES.FINANCES_INSTALLMENT_PLANS` (Next `Link` ou `<a>`); **sem** string crua de rota (DRY) |
| **`Link` do Next (navegação interna)** | `frontend/components/layouts/sidebar.tsx` (uso de `next/link` com `href={ROUTES...}`) | Idioma do link interno. Em modal Radix, `Link` funciona; o alvo é uma rota do dashboard |
| Mock policy / MSW | `frontend/CLAUDE.md` (MSW só fronteira HTTP; sem mock de componente interno) + teste existente :9-22 (mocka **hooks de dados/mutations** — fronteira de API, padrão já estabelecido neste arquivo) | Manter o padrão de mock **já usado** neste arquivo de teste (mock dos hooks `use-bills`/`use-buildings`/etc.); **não** introduzir mock de componente UI interno |

### O que S56–S61 já entregaram (PRÉ-REQUISITO desta sessão — NÃO recriar)

- **S56** (BE): `BillingAccount.account_type` (enum `BillingAccountType`: `water/electricity/iptu/internet/generic`), `holder_name`/`registered_address`/`secondary_identifier`/`supply_status`, unique identity `(building, account_type, external_identifier)`, `recurring_for_generation()`.
- **S58** (BE): `WaterBillStatement`/`ElectricityBillStatement` (1:1 com `Bill`), `create_with_lines`/`update_with_lines` estendidos, nested serializer (`water_statement`/`electricity_statement`), RLS.
- O `bill.schema.ts` já tem `external_identifier`/`issue_date` (`:30`); o `bill-form-modal.tsx` já carrega/envia ambos no `emptyDefaults`/`billToDefaults`/payload (UI-only nesta sessão).

> **Dependências desta sessão: S56 (account_type) + S58 (statements/serializer).** Esta sessão é **frontend-only de layout/campos** e **não** depende do parser (S60) nem do alerta (S61). **Se S56/S58 não estiverem concluídas, PARE** (o `bill.schema.ts` precisa dos campos). A **renderização** do bloco de statement (água/luz condicional) é **desta** sessão (S62, dona do layout/campos do modal); o **prefill do statement a partir do draft do parser** + o **botão "Importar fatura" + `useParseInvoice` + `IptuRiskBanner`** são da **S63** — **não** fazer aqui.

---

## Escopo

### Arquivos a criar
- `frontend/components/ui/__tests__/dialog-body.test.tsx` — testes da primitiva `DialogBody` (render, `flex-1 overflow-y-auto`, repasse de `className`/`children`, `displayName`).

### Arquivos a modificar
- `frontend/components/ui/dialog.tsx` — **adicionar** `DialogBody` (componente funcional `flex-1 overflow-y-auto`, espelhando `DialogHeader`/`DialogFooter` :56-82) e incluí-lo no `export {...}` (:111-122). **Não** alterar `DialogContent`/`DialogHeader`/`DialogFooter` existentes (a classe `max-h-[90vh] flex flex-col` é aplicada **por consumidor** via `className`, não embutida na primitiva — KISS).
- `frontend/app/(dashboard)/finances/bills/_components/bill-form-modal.tsx` — (1) `DialogContent` → `max-h-[90vh] max-w-3xl flex flex-col` (remover `overflow-y-auto` da `DialogContent`); (2) envolver o `<Form>`/corpo num `<DialogBody>`; o `<DialogFooter>` vira **irmão** do `DialogBody` (fora do scroll) — mover para fora do `<form>`? Não: manter o `<form>` envolvendo header-implícito? **Decisão pinada abaixo** (§"Estrutura do `<form>` × `DialogBody`/footer fixo"); (3) **renderizar** os inputs `external_identifier` (label "Inscrição/UC") e `issue_date` (label "Emissão", `type="date"`) no grid (já no schema/payload — só UI); (4) **renderizar o bloco de statement condicional ao `account_type`** (água/luz; oculto para IPTU/genérica) com inputs editáveis readings-only (§"Bloco de statement condicional"); (5) trocar o `Alert` "Fase 3" (:362-370) por um bloco com **link para Planos de Parcelamento** (`ROUTES.FINANCES_INSTALLMENT_PLANS`) mantendo o **bloqueio do submit** quando `isInstallment`.
- `frontend/app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx` — **reescrever** o teste `:115-126` (assertar o link "Planos de Parcelamento" + `href`, em vez de `/Fase 3/i`); **manter** que `isInstallment` bloqueia o submit. Demais testes **intactos** (incluindo os que afirmam labels/criar/atualizar).
- `frontend/app/(dashboard)/finances/employees/_components/employee-form-modal.tsx` — `DialogContent` → `max-h-[90vh] max-w-3xl flex flex-col` (sem `overflow-y-auto`); corpo no `<DialogBody>`; footer irmão.
- `frontend/app/(dashboard)/finances/installment-plans/_components/installment-plan-form-modal.tsx` — idem (`DialogContent :156`).
- `frontend/app/(dashboard)/finances/income-entries/_components/income-entry-form-modal.tsx` — `DialogContent` (:147, hoje `max-w-lg`) → `max-w-lg max-h-[90vh] flex flex-col`; corpo no `<DialogBody>`; footer irmão.

### NÃO fazer (pertence a outras sessões / fora de escopo)
- **`useParseInvoice` / `useUpdateBillWithLines` / botão "Importar fatura (PDF)" / `IptuRiskBanner` / `use-iptu-alerts`** — é a **Sessão 63** (depende de S60 parser + S61 alerta). **Não** criar hooks de API nem tocar `use-bills.ts`/`bill.schema.ts` aqui.
- **Prefill do bloco de statement a partir do draft do parser** (`useParseInvoice` → `draft.statement`) — é a **Sessão 63**. Esta sessão **renderiza** o bloco de statement condicional (inputs editáveis, vazios no fluxo manual); a S63 apenas **pré-preenche** esses campos a partir do `draft.statement`. A renderização/condicional pertence a **esta** sessão (S62), que é dona do layout/campos do `bill-form-modal`.
- **Desambiguação dos selects de conta** (`name — tipo · external_identifier`) — é a **Sessão 63** (depende do `account_type`/`external_identifier` nas opções de `billing-account.schema`). **Não** mexer no `SelectItem` da "Conta recorrente" agora.
- **`billing-account-form-modal.tsx`** — **não existe** neste repositório (não há `finances/billing-accounts/_components/`). A tarefa lista-o como "irmão a alinhar", mas como **não existe**, **não** criá-lo (YAGNI/KISS). Alinhar **apenas** os 3 modais que existem (`employee`, `installment-plan`, `income-entry`). Se uma sessão futura criar o `billing-account-form-modal`, ela já nasce com `DialogBody`.
- **Legado `app/(dashboard)/financial/*`** (módulo financeiro antigo) — fora de escopo (design §8.1). **Não** tocar `contract-view-modal.tsx` (já está correto à mão).
- **Backend** (serializers/viewsets/parser/alerta/migração) — sessões 56–61/63/64.

---

## Especificação

> Frontend Next.js 14 + React 18, TanStack Query v5, React Hook Form + Zod, Shadcn/Radix Dialog, Tailwind. `camelCase`/`PascalCase`; named exports; `import type` p/ tipos; `@/` alias. **Sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção (`noUncheckedIndexedAccess`). Textos ao usuário em **PT**.

### `DialogBody` — primitiva reutilizável (design §8.1)

Adicionar em `frontend/components/ui/dialog.tsx`, **espelhando** `DialogHeader`/`DialogFooter` (`:56-82` — componente funcional, não `forwardRef`; os headers/footers do projeto não usam ref):

```tsx
const DialogBody = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex-1 overflow-y-auto", className)}
    {...props}
  />
)
DialogBody.displayName = "DialogBody"
```

- Incluir `DialogBody` no bloco `export {...}` (`:111-122`), em ordem coerente (após `DialogFooter`).
- **Decisão (KISS):** `DialogBody` carrega **só** `flex-1 overflow-y-auto`. A classe `max-h-[90vh] flex flex-col` fica no **`DialogContent` do consumidor** (via `className`) — igual ao `contract-view-modal`. A primitiva não impõe `max-h`/`flex-col` (um `DialogContent` curto não precisa). **Não** embutir essas classes na primitiva `DialogContent` (quebraria os modais curtos do projeto que dependem do `grid` atual).

### Estrutura do `<form>` × `DialogBody`/footer fixo (decisão pinada)

O footer precisa ficar **fora** da área que rola, mas o botão `type="submit"` precisa estar **dentro** do mesmo `<form>` que o corpo (RHF `handleSubmit`). Logo, o `<form>` envolve **ambos** `DialogBody` (corpo rolável) **e** `DialogFooter` (fixo), e o `<form>` é o filho flex que estica:

```tsx
<DialogContent className="max-h-[90vh] max-w-3xl flex flex-col">
  <DialogHeader> … </DialogHeader>           {/* fixo (não rola) */}
  <Form {...form}>
    <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="flex flex-1 flex-col overflow-hidden">
      <DialogBody className="space-y-4 pr-1">  {/* SÓ o corpo rola */}
        {/* grid de campos + line items + alerts + notas */}
      </DialogBody>
      <DialogFooter className="pt-4">          {/* fixo, fora do scroll */}
        <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
        <Button type="submit" disabled={…}>{isEdit ? 'Atualizar' : 'Criar'}</Button>
      </DialogFooter>
    </form>
  </Form>
</DialogContent>
```

- O `<form>` recebe `flex flex-1 flex-col overflow-hidden` → estica para preencher o `DialogContent` (`flex flex-col`) e contém o scroll no `DialogBody`. O `DialogFooter` fica abaixo, **sempre visível**.
- O `space-y-4` que hoje está no `<form>` migra para o `DialogBody` (o corpo). `pr-1` evita o scrollbar colar nos campos (cosmético, opcional mas recomendado).
- **Igual** nos 4 modais (DRY de estrutura): header fora do `<form>`, `DialogBody` + `DialogFooter` dentro do `<form>`. `income-entry` usa `onSubmit={form.handleSubmit(onSubmit)}` (async) — mesma estrutura.

### Campos Inscrição/UC + Emissão no `bill-form-modal` (design §8.2 — UI-only)

`external_identifier` e `issue_date` **já** estão no `BillFormValues`/`emptyDefaults`/`billToDefaults`/payload (`:53-88`, `:157-174`) — esta sessão **só renderiza os inputs** no grid 1/2-col (não toca schema/payload). Adicionar dois `FormField` no grid (após "Vencimento", antes do `behavior==='recurring'` billing_account):

```tsx
<FormField
  control={form.control}
  name="external_identifier"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Inscrição / UC (opcional)</FormLabel>
      <FormControl>
        <Input placeholder="Inscrição municipal / Unidade Consumidora" {...field} />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>

<FormField
  control={form.control}
  name="issue_date"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Emissão (opcional)</FormLabel>
      <FormControl>
        <Input type="date" value={field.value ?? ''} onChange={(e) => field.onChange(e.target.value || null)} />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

- `issue_date` é `string | null` no schema (`:30` `z.string().nullable().optional()`) → `value={field.value ?? ''}` e `onChange` mapeia `'' → null` (não passar `null` cru a `<input value>` — `noUncheckedIndexedAccess`/React warning). `external_identifier` é `string` com default `''` → `{...field}` direto.
- **Não** adicionar validação nova (os campos são opcionais — design §8.2). A obrigatoriedade de `external_identifier` para água/luz/IPTU é do **backend** (S56 `clean()`/serializer) — o front não duplica essa regra aqui (KISS; o erro do serializer aparece via `handleError`).

### Bloco de statement condicional ao `account_type` (design §8.2 — readings-only, editável)

Esta sessão é dona do **layout e dos campos** do `bill-form-modal`, incluindo o bloco de statement. Renderizar, **condicional ao `account_type` selecionado** (`account_type ∈ {water, electricity}` → visível; IPTU/genérica → **oculto**), um bloco de inputs **editáveis** readings-only (NENHUM campo de dinheiro — o dinheiro é `BillLineItem`). Os campos espelham `WaterBillStatement`/`ElectricityBillStatement` (S58) e os schemas aninhados `water_statement`/`electricity_statement` (S63 ainda os define no `bill.schema.ts`; aqui o bloco lê/escreve os mesmos nomes):

- **água** (`account_type === 'water'`): `consumo_m3`, `leitura_anterior`, `leitura_atual`, `leitura_dias`, `data_leitura` (`type="date"`), `agua_status` (select `active`/`cut`), `esgoto_status` (select `active`/`cut`).
- **luz** (`account_type === 'electricity'`): `consumo_kwh`, `energia_injetada_kwh`, `leitura_anterior`, `leitura_atual`, `leitura_dias`, `classe`, `bandeira`.

- No fluxo **manual** (Nova Conta), os campos nascem **vazios e editáveis** (o admin pode preencher). O **prefill a partir do `draft.statement`** do parser é da **S63** — esta sessão só renderiza/condiciona; não consome `useParseInvoice` nem mapeia o draft.
- O bloco vive dentro do `<DialogBody>` (corpo rolável), após os campos do cabeçalho. Inputs controlados via `field.value ?? ''` (sem `as`/`!`).
- **Não** desambiguar os selects de conta aqui (`name — tipo · external_identifier`) — isso é **S63**.

### Alerta "Fase 3" → link Planos de Parcelamento (design §8.2)

Trocar o `Alert` `isInstallment` (`:362-370`) por um bloco que **mantém o bloqueio do submit** (`handleSubmit` já retorna cedo quando `isInstallment` — `:119-123` — e o botão fica `disabled`) mas direciona o usuário ao lugar certo:

```tsx
{isInstallment && (
  <Alert>
    <Info className="h-4 w-4" />
    <AlertDescription>
      Contas parceladas são geridas em{' '}
      <Link
        href={ROUTES.FINANCES_INSTALLMENT_PLANS}
        className="font-medium underline underline-offset-4"
      >
        Planos de Parcelamento
      </Link>
      . Selecione outro tipo para salvar aqui.
    </AlertDescription>
  </Alert>
)}
```

- `import Link from 'next/link'` e `import { ROUTES } from '@/lib/utils/constants'`. **Sem** string de rota crua.
- O `Link` é acessível como `role="link"` com `href={ROUTES.FINANCES_INSTALLMENT_PLANS}` (`/finances/installment-plans`) → o teste reescrito assere isso.
- **Manter** o bloqueio: `handleSubmit` retorna sem mutar quando `isInstallment` (`:120-123` intacto); o botão `type="submit"` segue `disabled={isInstallment || …}` (`:404`). O texto "Fase 3" some (a fase 3 já existe — Planos de Parcelamento é a tela real).
- O `Alert` edit-locked (`:372-379` "As linhas só podem ser definidas na criação") **permanece intacto** (não é "Fase 3").

### Alinhamento dos modais irmãos (mesma estrutura, sem mudar comportamento)

Para `employee-form-modal`, `installment-plan-form-modal`, `income-entry-form-modal`: aplicar **só** a reestruturação de layout (`DialogContent` `flex flex-col` + `DialogBody` + footer irmão). **Nenhuma** mudança de campos, validação, hooks, labels, textids, `aria-label` ou comportamento de submit — os testes deles assertam **labels/roles/testids/texto**, não DOM nesting (design §8.1). `income-entry` mantém o `max-w-lg` (largura menor); os outros mantêm `max-w-3xl`.

---

## TDD — ciclo obrigatório (Red → Green → Refactor → Verify)

> **Mock policy** (`frontend/CLAUDE.md`): mockar **APENAS fronteiras** — neste arquivo de teste, as fronteiras já mockadas são os **hooks de API** (`use-bills`/`use-buildings`/`use-finance-categories`/`use-billing-accounts` — `:9-22`). **NUNCA** mockar componentes UI internos (`DialogBody`/`BillFormModal`/`Alert`). `renderWithProviders` real; Radix Select via `userEvent` (polyfills `:39-48` já presentes). `DialogBody` é puro (sem hooks/API) → teste de unidade direto. Vitest + Testing Library; zero warnings.

### 1. RED — escrever/reescrever os testes primeiro

#### `frontend/components/ui/__tests__/dialog-body.test.tsx` (NOVO)

```ts
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DialogBody } from '@/components/ui/dialog';

describe('DialogBody', () => {
  it('renders children inside a scrollable flex-1 region', () => {
    // DialogBody is the rolling area: it must carry `flex-1` (stretch in the
    // flex-col DialogContent) and `overflow-y-auto` (only the body scrolls).
    render(<DialogBody data-testid="body">conteúdo</DialogBody>);
    const body = screen.getByTestId('body');
    expect(body).toHaveTextContent('conteúdo');
    expect(body.className).toContain('flex-1');
    expect(body.className).toContain('overflow-y-auto');
  });

  it('merges a consumer className without dropping the base classes', () => {
    // cn() keeps flex-1/overflow-y-auto and appends the consumer spacing class.
    render(<DialogBody data-testid="body" className="space-y-4 pr-1">x</DialogBody>);
    const body = screen.getByTestId('body');
    expect(body.className).toContain('flex-1');
    expect(body.className).toContain('overflow-y-auto');
    expect(body.className).toContain('space-y-4');
  });

  it('forwards arbitrary div props (role) to the underlying element', () => {
    // It is a plain div primitive — extra HTML attributes pass straight through.
    render(<DialogBody role="group" aria-label="corpo">x</DialogBody>);
    expect(screen.getByRole('group', { name: 'corpo' })).toBeInTheDocument();
  });

  it('exposes a stable displayName for devtools/debugging', () => {
    // Mirrors DialogHeader/DialogFooter which set displayName explicitly.
    expect(DialogBody.displayName).toBe('DialogBody');
  });
});
```

#### `frontend/app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx` (REESCREVER `:115-126`, ADICIONAR cobertura)

**Reescrever** o teste atual `blocks installment behavior with a Portuguese Phase 3 note` para assertar o **link** (não `/Fase 3/i`) e **manter** o bloqueio do submit:

```ts
it('links installment behavior to Planos de Parcelamento and blocks submission', async () => {
  // The stale "Fase 3" copy is replaced by a real link to the Installment Plans
  // screen; selecting "Parcelada" must still block create (handled elsewhere).
  const { creates } = mountCreate();
  const user = userEvent.setup({ pointerEventsCheck: 0 });
  renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

  await user.click(screen.getByLabelText('Tipo'));
  await user.click(await screen.findByRole('option', { name: 'Parcelada' }));

  const link = await screen.findByRole('link', { name: /Planos de Parcelamento/i });
  expect(link).toHaveAttribute('href', '/finances/installment-plans');

  await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));
  expect(creates).toHaveLength(0);
});
```

**Adicionar** dois testes novos (campos Inscrição/Emissão + footer visível):

```ts
it('renders Inscrição/UC and Emissão inputs and includes them in the create payload', async () => {
  // external_identifier + issue_date are already in the schema/payload; this
  // session only renders the inputs — assert they round-trip into the mutation.
  const { creates } = mountCreate();
  renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

  fireEvent.change(screen.getByPlaceholderText('Descrição da conta'), {
    target: { value: 'Conta de Água' },
  });
  fireEvent.change(screen.getByLabelText('Competência'), { target: { value: '2026-06-01' } });
  fireEvent.change(screen.getByLabelText('Vencimento'), { target: { value: '2026-06-10' } });
  fireEvent.change(screen.getByLabelText('Inscrição / UC (opcional)'), {
    target: { value: 'UC-12345' },
  });
  fireEvent.change(screen.getByLabelText('Emissão (opcional)'), { target: { value: '2026-06-02' } });
  fireEvent.change(screen.getByPlaceholderText('Ex: Consumo de energia'), {
    target: { value: 'Consumo' },
  });
  fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '120' } });

  await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

  await waitFor(() => {
    expect(creates).toHaveLength(1);
  });
  expect(creates[0]?.payload.bill).toMatchObject({
    external_identifier: 'UC-12345',
    issue_date: '2026-06-02',
  });
});

it('keeps the submit footer rendered (fixed) outside the scrolling body', () => {
  // Footer lives as a sibling of DialogBody (not inside the overflow region),
  // so the action buttons are always present regardless of body length.
  mountCreate();
  renderWithProviders(<BillFormModal open onClose={vi.fn()} />);
  expect(screen.getByRole('button', { name: /^criar$/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^cancelar$/i })).toBeInTheDocument();
});

it('shows the statement block for water/electricity accounts and hides it for generic/iptu', async () => {
  // The statement block (readings-only inputs) is conditional on the selected
  // account_type: visible for water (consumo_m3) / electricity (consumo_kwh),
  // hidden for generic and iptu. Manual flow: fields render empty and editable.
  mountCreate();
  const user = userEvent.setup({ pointerEventsCheck: 0 });
  renderWithProviders(<BillFormModal open onClose={vi.fn()} />);

  // generic/iptu → no statement inputs
  expect(screen.queryByLabelText('Consumo (m³)')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Consumo (kWh)')).not.toBeInTheDocument();

  // select water → consumo_m3 input appears (editable, empty)
  await user.click(screen.getByLabelText('Tipo de conta'));
  await user.click(await screen.findByRole('option', { name: /Água/i }));
  expect(await screen.findByLabelText('Consumo (m³)')).toBeInTheDocument();
  expect(screen.queryByLabelText('Consumo (kWh)')).not.toBeInTheDocument();

  // select electricity → consumo_kwh input appears, consumo_m3 disappears
  await user.click(screen.getByLabelText('Tipo de conta'));
  await user.click(await screen.findByRole('option', { name: /Luz/i }));
  expect(await screen.findByLabelText('Consumo (kWh)')).toBeInTheDocument();
  expect(screen.queryByLabelText('Consumo (m³)')).not.toBeInTheDocument();
});
```
> O `account_type` é o seletor existente do modal (label/option conforme o `bill-form-modal` real — ajustar o `getByLabelText`/`option name` ao texto efetivo). O teste afirma **presença/ausência** condicional dos inputs do statement, não medição de layout.

> **Nota de fronteira (jsdom):** jsdom não calcula layout, então o teste do footer **não** mede pixels — ele afirma a **presença** dos botões (a fixação real é garantida pela estrutura `DialogBody` irmão do `DialogFooter`, verificada visualmente/por classe). Para travar a estrutura, o teste de `DialogBody` (acima) cobre `flex-1 overflow-y-auto`. **Não** inventar medição de viewport em jsdom (seria mock de layout — proibido).

> Rodar (devem **falhar** — `DialogBody` ainda não existe; o link ainda não substituiu "Fase 3"; os inputs Inscrição/Emissão ainda não são renderizados):
> ```bash
> cd frontend && npx vitest run "components/ui/__tests__/dialog-body.test.tsx" "app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx"
> ```

### 2. GREEN — implementar

1. `frontend/components/ui/dialog.tsx` — adicionar `DialogBody` (`flex-1 overflow-y-auto`, `displayName`) + incluir no `export {...}`.
2. `bill-form-modal.tsx` — `DialogContent` `max-h-[90vh] max-w-3xl flex flex-col` (remover `overflow-y-auto`); `<form>` ganha `flex flex-1 flex-col overflow-hidden`; corpo (grid + line items + alerts + notas) dentro de `<DialogBody className="space-y-4 pr-1">`; `<DialogFooter>` irmão do `DialogBody` (dentro do `<form>`). Renderizar os 2 inputs (Inscrição/UC, Emissão). Trocar o `Alert` "Fase 3" pelo link a `ROUTES.FINANCES_INSTALLMENT_PLANS` (import `Link` de `next/link` + `ROUTES`).
3. `employee-form-modal.tsx`, `installment-plan-form-modal.tsx`, `income-entry-form-modal.tsx` — mesma reestruturação (`DialogContent` flex-col + `<DialogBody>` + footer irmão). Nada além de layout.

Rodar até verde:
```bash
cd frontend && npx vitest run "components/ui/__tests__/dialog-body.test.tsx" "app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx"
```

### 3. REFACTOR — DRY / clareza (sem mudar comportamento)
- A estrutura `DialogContent flex-col → DialogHeader (fora) → <form> flex-1 flex-col overflow-hidden → DialogBody + DialogFooter` é **idêntica** nos 4 modais — aplicar o mesmo idioma (não criar um wrapper especulativo "FormDialog"; YAGNI — só repetir o padrão simples e legível em cada modal).
- O link "Planos de Parcelamento" usa `ROUTES.FINANCES_INSTALLMENT_PLANS` (constante única); zero string de rota crua.
- Confirmar que `external_identifier`/`issue_date` **não** duplicam lógica de schema/payload (já existem — só `FormField`). `issue_date` mapeia `'' → null` num único lugar (o `onChange` do próprio campo).
- Nenhum `as`/`!` em produção; `field.value ?? ''` para os `value` de input controlado.

### 4. VERIFY — gate frontend (escopo desta sessão)

```bash
cd frontend
npx vitest run "components/ui/__tests__/dialog-body.test.tsx" \
  "app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx" \
  "app/(dashboard)/finances/employees/_components/__tests__/employee-form-modal.test.tsx" \
  "app/(dashboard)/finances/installment-plans/_components/__tests__/installment-plan-form-modal.test.tsx" \
  "app/(dashboard)/finances/income-entries/__tests__/income-entry-form-modal.test.tsx"
npm run type-check
npx eslint "components/ui/dialog.tsx" "components/ui/__tests__/dialog-body.test.tsx" \
  "app/(dashboard)/finances/bills/_components/bill-form-modal.tsx" \
  "app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx" \
  "app/(dashboard)/finances/employees/_components/employee-form-modal.tsx" \
  "app/(dashboard)/finances/installment-plans/_components/installment-plan-form-modal.tsx" \
  "app/(dashboard)/finances/income-entries/_components/income-entry-form-modal.tsx"
```

> **Regressão obrigatória dos modais irmãos** (não quebrar): os 3 testes de modal irmão (employee/installment-plan/income-entry) **rodam verdes sem edição** — eles assertam labels/roles/testids, não DOM nesting (design §8.1). Se algum quebrar, é sinal de que o refactor mudou comportamento (não deveria) — **corrigir o modal**, não o teste. Antes de fechar, rodar `npm run lint && npm run type-check && npm run test:unit` (suite completa do front) para confirmar zero erros/warnings globais.

---

## Constraints

- **Layout só por consumidor**: `DialogBody` carrega **só** `flex-1 overflow-y-auto`; `max-h-[90vh] flex flex-col` fica no `DialogContent` de cada modal (via `className`). **Não** embutir `max-h`/`flex-col` na primitiva `DialogContent` (quebraria os modais curtos `grid` do projeto).
- **Footer fixo = footer irmão do `DialogBody`** dentro do `<form>` (`<form>` com `flex flex-1 flex-col overflow-hidden`); **só** o `DialogBody` rola. Header **fora** do `<form>` (não rola).
- **Inscrição/UC + Emissão são UI-only**: `external_identifier`/`issue_date` já no schema/payload — **só** renderizar `FormField`. **Não** alterar `bill-form-schema`/`bill.schema.ts`/payload nem adicionar validação (opcionais; obrigatoriedade água/luz/IPTU é do backend S56).
- **Link, não "Fase 3"**: trocar o alerta pelo link `ROUTES.FINANCES_INSTALLMENT_PLANS` mantendo o **bloqueio do submit** (`handleSubmit` early-return + botão `disabled`). **Reescrever** o teste `:115-126` (assertar o link), **não** deletá-lo. O `Alert` edit-locked permanece.
- **Modais irmãos: só layout** — zero mudança de campos/validação/hooks/labels/testids/comportamento. `income-entry` mantém `max-w-lg`; os outros `max-w-3xl`.
- **`billing-account-form-modal` não existe** → **não** criá-lo (YAGNI). Alinhar só os 3 que existem.
- **Sem S63/backend aqui**: nenhum `useParseInvoice`/`useUpdateBillWithLines`/"Importar fatura"/`IptuRiskBanner`/`use-iptu-alerts`/prefill do statement a partir do draft/desambiguação de select. **A renderização do bloco de statement (condicional ao `account_type`) É desta sessão.** Nenhuma edição de `use-bills.ts`/`bill.schema.ts`. Nenhuma edição de `contract-view-modal.tsx`/legado `financial/*`.
- **Sem suppressions**: proibido `eslint-disable`/`@ts-ignore`/`@ts-expect-error`/`as`/`!` em produção. Inputs controlados via `field.value ?? ''`. Tipos completos (TS strict + `noUncheckedIndexedAccess`).
- **Named exports**, `import type` p/ tipos, `@/` alias, `next/link` para navegação interna. **Sem** re-export/barrel novo.
- **Mock policy**: só fronteira (hooks de API já mockados no arquivo de teste); **nunca** mockar `DialogBody`/`Alert`/`BillFormModal`. `DialogBody` é puro → teste direto.
- Textos ao usuário em **Português**; nomes de identificadores/classes em **Inglês**.

## Critérios de Aceite (binários)

- [ ] `frontend/components/ui/dialog.tsx` exporta `DialogBody` (`flex-1 overflow-y-auto`, `displayName="DialogBody"`, repassa `className` via `cn` e props de `div`); `DialogContent`/`DialogHeader`/`DialogFooter` **intactos**.
- [ ] `bill-form-modal.tsx`: `DialogContent="max-h-[90vh] max-w-3xl flex flex-col"` (sem `overflow-y-auto`); `<form>` `flex flex-1 flex-col overflow-hidden`; corpo dentro de `<DialogBody className="space-y-4 pr-1">`; `<DialogFooter>` **irmão** do `DialogBody` (footer fixo). Header fora do `<form>`.
- [ ] `bill-form-modal.tsx` renderiza os inputs **Inscrição / UC (opcional)** (`external_identifier`) e **Emissão (opcional)** (`issue_date`, `type=date`, `'' → null`); ambos round-trip no payload de criação (teste). Schema/payload **não** alterados.
- [ ] `bill-form-modal.tsx` renderiza o **bloco de statement condicional ao `account_type`** com inputs editáveis readings-only — água (`consumo_m3`/`leitura_anterior`/`leitura_atual`/`leitura_dias`/`data_leitura`/`agua_status`/`esgoto_status`) e luz (`consumo_kwh`/`energia_injetada_kwh`/`leitura_anterior`/`leitura_atual`/`leitura_dias`/`classe`/`bandeira`); **oculto** para IPTU/genérica; teste cobre visível para água/luz, oculto para genérica/iptu. **Sem** campos de dinheiro; **sem** prefill a partir do parser (S63).
- [ ] Alerta "Fase 3" substituído por **link** a `ROUTES.FINANCES_INSTALLMENT_PLANS` (`/finances/installment-plans`, `role="link"`), mantendo o **bloqueio do submit** quando `isInstallment`; `Alert` edit-locked intacto.
- [ ] Teste `bill-form-modal.test.tsx:115-126` **reescrito** (assertar o link + `href` + submit bloqueado), não deletado; testes de criar/atualizar/validação/recurring **intactos** e verdes.
- [ ] `employee-form-modal`, `installment-plan-form-modal`, `income-entry-form-modal` migrados para `max-h-[90vh] flex flex-col` + `DialogBody` + footer irmão; **só layout**; seus testes existentes seguem verdes **sem edição**.
- [ ] `DialogBody` 100% responsivo dentro do `DialogContent` (`w-[calc(100vw-2rem)]` herdado; grid 1-col mobile / 2-col `sm+`; footer sempre visível).
- [ ] `npx vitest run` nos 5 arquivos passa 100%; `npm run lint` + `npm run type-check` + `npm run test:unit` (suite completa) **zero erros e zero warnings**; **sem** `eslint-disable`/`@ts-ignore`/`as`/`!` em produção.
- [ ] Nenhum `useParseInvoice`/"Importar fatura"/`IptuRiskBanner`/prefill do statement a partir do draft/desambiguação de select/edição de `use-bills.ts`/`bill.schema.ts`/`contract-view-modal.tsx`/legado `financial/*`; nenhum `billing-account-form-modal` criado; nenhum backend tocado. (A **renderização** do bloco de statement É desta sessão.)

## Handoff

1. Rodar e confirmar verde (gate frontend, escopo desta sessão):
   ```bash
   cd frontend
   npx vitest run "components/ui/__tests__/dialog-body.test.tsx" \
     "app/(dashboard)/finances/bills/_components/__tests__/bill-form-modal.test.tsx" \
     "app/(dashboard)/finances/employees/_components/__tests__/employee-form-modal.test.tsx" \
     "app/(dashboard)/finances/installment-plans/_components/__tests__/installment-plan-form-modal.test.tsx" \
     "app/(dashboard)/finances/income-entries/__tests__/income-entry-form-modal.test.tsx"
   npm run lint && npm run type-check && npm run test:unit
   ```
2. Anotar para o orquestrador atualizar `prompts/SESSION_STATE.md` (NÃO editar `ROADMAP.md`/`SESSION_STATE.md`):
   - Linha da Sessão 62 (status **concluída**) na tabela da feature "Contas de utilidade do condomínio".
   - **Arquivos Criados**: `frontend/components/ui/__tests__/dialog-body.test.tsx`.
   - **Arquivos Modificados**: `frontend/components/ui/dialog.tsx` (`DialogBody`), `bills/_components/bill-form-modal.tsx` (layout + Inscrição/Emissão + link Planos de Parcelamento), `bills/_components/__tests__/bill-form-modal.test.tsx` (reescrito 115-126 + 2 testes novos), `employees/_components/employee-form-modal.tsx`, `installment-plans/_components/installment-plan-form-modal.tsx`, `income-entries/_components/income-entry-form-modal.tsx` (layout DialogBody).
   - **Nota**: "Fase 6a (FE layout): `DialogBody` (`flex-1 overflow-y-auto`) reutilizável; modal Nova Conta com header/footer fixos, corpo rola; inputs Inscrição/UC + Emissão (UI-only, já no schema/payload); **bloco de statement condicional ao `account_type` (água/luz, readings-only editável; oculto IPTU/genérica)**; alerta 'Fase 3' → link Planos de Parcelamento; 3 modais irmãos alinhados (só layout). **Sem `useParseInvoice`/'Importar fatura'/`IptuRiskBanner`/prefill do statement a partir do draft/desambiguação de select = S63; sem backend.** `billing-account-form-modal` não existe → não criado (YAGNI)."
   - **Contratos cross-session** (verbatim, ver abaixo).
3. Rodar `/audit` (skill `audit`) contra esta seção de Critérios de Aceite e corrigir gaps antes de fechar.
4. Commitar (a partir de `master`/branch da feature — ex.: `feat/condo-utility-bills`):
   ```
   feat(finances): complete session 62 — DialogBody + responsive Nova Conta modal (fixed header/footer, Inscrição/Emissão, Planos de Parcelamento link) + align sibling finances modals

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Próxima sessão: **63 — Frontend: importar fatura + banner IPTU** (`useParseInvoice` multipart + `useUpdateBillWithLines`, botão "Importar fatura (PDF)" admin-only ao lado de "Nova Conta", bloco de statement água/luz condicional, desambiguação dos selects de conta, `IptuRiskBanner` + `use-iptu-alerts` uncached) — consome o `DialogBody`/modal desta sessão (S62), o parser (S60) e o alerta (S61). A S63 **adiciona** sobre o layout desta sessão; **não** recria o `DialogBody` nem reestrutura os modais.

---

### Contratos cross-session definidos por esta sessão (consumir verbatim)

- **`DialogBody`** (`@/components/ui/dialog`): `({ className, ...props }: React.HTMLAttributes<HTMLDivElement>)` → `<div className={cn("flex-1 overflow-y-auto", className)} {...props} />`, `displayName="DialogBody"`. **S63** usa-o para o bloco de statement e o painel de import dentro do modal Nova Conta (corpo rolável). Modais longos usam `DialogContent className="max-h-[90vh] ... flex flex-col"` + `<form className="flex flex-1 flex-col overflow-hidden">` (header fora do `<form>`, `DialogBody` + `DialogFooter` dentro).
- **Estrutura do `bill-form-modal`**: header fixo / `DialogBody` (grid 1-col mobile / 2-col `sm+`, com Inscrição/UC + Emissão **e o bloco de statement condicional ao `account_type` — água/luz, readings-only editável; oculto IPTU/genérica — renderizados nesta sessão**) / `DialogFooter` fixo. **S63** apenas **pré-preenche** o bloco de statement a partir do `draft.statement` do parser e insere o **painel "Importar fatura"** dentro do `DialogBody` (não recria a estrutura nem o bloco), e a **desambiguação** dos `SelectItem` de conta (`name — tipo · external_identifier`).
- **Link Planos de Parcelamento**: `ROUTES.FINANCES_INSTALLMENT_PLANS` (`/finances/installment-plans`) é o destino canônico para contas parceladas (substitui a copy "Fase 3"). **S63** não reverte isso.
- **Modais irmãos alinhados** (`employee`/`installment-plan`/`income-entry`) já usam `DialogBody` — qualquer modal novo do `finances` (incl. um futuro `billing-account-form-modal`) **nasce** com este padrão.
