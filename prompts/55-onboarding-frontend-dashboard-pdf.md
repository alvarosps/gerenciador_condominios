# Sessão 55 — Frontend: CTA no dashboard + passo de PDF + e2e/polish/audit

> **Feature**: Fluxo "Novo inquilino + contrato" (web) — `docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
> **Sessões**: 51 → 52 → 53 → 54 → **55** (final). Esta liga o **CTA "Novo inquilino + contrato"** no dashboard (gated `is_staff`), adiciona o **passo 6 (PDF opcional)** ao wizard reusando `useGenerateContract`, e fecha a feature (e2e + polish + `/audit`).
> **Depende de**: **S54** (wizard + `onSuccess(tenant, lease)`) e **S51** (guard de locador → 400 no `generate_contract`). **Se a S54 não estiver concluída, PARE.**
> **Branch**: `feat/tenant-lease-onboarding`.

---

## Contexto

Ler antes de codar:
- **Design doc** (ler §4.3 passo 6 + §4.4 entrada, §5 G2/G8): `@docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Estado**: `@prompts/SESSION_STATE.md` (contratos S52/S54 verbatim)
- **Frontend rules**: `@frontend/CLAUDE.md`

### Exemplares (arquivo:symbol)

| Padrão | Local | Por quê |
|--------|-------|---------|
| Geração de PDF (hook + modal + download) | `frontend/lib/api/hooks/use-leases.ts:140-149` (`useGenerateContract` → `{pdf_path,message}`); `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx:36-37` (extrai `pdf_path` → `/download?path=`); `frontend/app/download/route.ts` | Reusar no passo 6. **G8**: tratar também `202 {task_id}` (defensivo). |
| Dashboard (onde montar o CTA) | `frontend/app/(dashboard)/page.tsx` — stack `space-y-6` cuja **1ª linha hoje é `<FinanceKpiRow />`**, seguida de `RentCalendarSection`/`CombinedCalendarSection`/… | CTA entra como **1º filho** do `space-y-6` (acima do `FinanceKpiRow`), gated `is_staff`. |
| Handler MSW existente de PDF | `frontend/tests/mocks/handlers.ts:382` (`POST .../generate_contract/` → `{message, pdf_path}` 200) | **Estender** este handler p/ cobrir 202/400 (não duplicar). |
| UI reutilizável (opcional) | `frontend/components/ui/stat-card.tsx`, `amount-display.tsx` (novos, das KPIs de finanças) | Podem servir de base visual ao card do CTA (opcional). |
| Auth/`is_staff` | `frontend/store/auth-store.ts` (`useAuthStore`, `user.is_staff`) | Gating do CTA + campos admin. |
| Wizard (props) | `app/(dashboard)/_components/tenant-lease-onboarding/index.tsx` (S54: `{open,onOpenChange,onSuccess}`) | CTA controla `open`; passo 6 usa `onSuccess`. |
| Botão/Card UI | `frontend/components/ui/{button,card,dialog}.tsx` | Composição do CTA + estado de sucesso. |
| Backend resposta do generate_contract | `core/views.py:376-393` (eager `{pdf_path}` 200; async `{task_id}` 202; **400** sem locador — S51) + `condominios_manager/settings.py:520-522` (`CELERY_TASK_ALWAYS_EAGER = not CELERY_BROKER_URL`) | Shapes a tratar no passo 6. |

---

## Escopo

### Arquivos a criar
- `frontend/app/(dashboard)/_components/onboarding-cta.tsx` — card/botão "Novo inquilino + contrato" (gated `is_staff`) que abre o `TenantLeaseOnboardingWizard`.
- `frontend/app/(dashboard)/_components/tenant-lease-onboarding/steps/success-step.tsx` — passo 6 (sucesso + "Gerar contrato (PDF)" / "Concluir").
- Testes: `frontend/app/(dashboard)/_components/__tests__/onboarding-cta.test.tsx`, `.../tenant-lease-onboarding/__tests__/success-step.test.tsx`.

### Arquivos a modificar
- `frontend/app/(dashboard)/page.tsx` — montar `<OnboardingCta />` como **1º filho** do `<div className="space-y-6">` (acima de `<FinanceKpiRow />`), gated `is_staff`.
- `frontend/app/(dashboard)/_components/tenant-lease-onboarding/index.tsx` — após `onSuccess`, exibir o passo 6 (success-step) em vez de fechar direto; estado `created: {tenant, lease} | null`.
- `frontend/lib/api/hooks/use-leases.ts` — `useGenerateContract` retorna **união discriminada** `{ pdf_path } | { task_id, status }` (G8) sem quebrar o consumidor atual (`contract-generate-modal`).
- `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx` — tratar o caso `202` (mensagem "processando…") sem falso sucesso (G8) — alinhamento mínimo, pois passa a ser união.
- `frontend/tests/mocks/handlers.ts` — **estender o handler existente** `POST .../generate_contract/` (já presente, ~linha 382, retorna `{pdf_path}` 200) para também permitir simular `{task_id}` (202) e **400** (sem locador) nos testes do passo 6. Não duplicar o handler.

### NÃO fazer
- **NÃO** construir polling completo de task (design §2 YAGNI; prod é eager). Tratar 202 só defensivamente (mensagem).
- **NÃO** alterar o contrato de onboarding (S52) nem reabrir o wizard (S54). Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção.

---

## Especificação

### `OnboardingCta`
- Lê `user` de `useAuthStore`; se `!user?.is_staff` → renderiza `null` (esconde).
- Card de destaque (título "Novo inquilino + contrato", subtítulo curto PT, botão primário com ícone) → `onClick` abre o wizard (`open` state local). Passa `onSuccess` adiante (o wizard cuida do passo 6 internamente).
- Montado como **1º filho** do `<div className="space-y-6">` em `app/(dashboard)/page.tsx` (acima de `<FinanceKpiRow />` e dos demais widgets).

### Passo 6 — `success-step.tsx`
- Recebe `{ tenant, lease, onClose }`. Mostra resumo curto ("Inquilino X e contrato do apto Y criados").
- Botão **"Concluir"** → `onClose()` (fecha o wizard).
- Botão **"Gerar contrato (PDF)"** → `useGenerateContract().mutateAsync(lease.id)`:
  - resposta `{pdf_path}` → abrir `/download?path=<relativo>` (mesma extração do `contract-generate-modal`).
  - resposta `{task_id}` (202) → toast/inline "Contrato em processamento; baixe em instantes na tela de Contratos." (sem polling).
  - erro **400** (sem locador — S51) → `toast.error(getErrorMessage(...))` PT ("Nenhum locador ativo configurado…"); botão permanece disponível.
- Estado de loading (`Loader2`) durante a geração.

### `useGenerateContract` — união discriminada (G8)
```ts
type GenerateContractResult =
  | { pdf_path: string; message?: string }
  | { task_id: string; status: string };
```
- O hook retorna o corpo da resposta tal qual; o consumidor discrimina por `"pdf_path" in result`. Atualizar `contract-generate-modal.tsx` para checar `"pdf_path" in result` antes de extrair (evita falso sucesso no 202).

### Wizard — exibir passo 6
- No `index.tsx`, adicionar estado `created: {tenant, lease} | null`. O **handler de sucesso do submit** (que na S54 fechava o Dialog) passa a: setar `created`, disparar `props.onSuccess?.(tenant, lease)` e **renderizar o `success-step`** (não fechar). "Concluir" (no success-step) reseta `created` e chama `props.onOpenChange(false)`.

---

## TDD — Red → Green → Refactor → Verify

> **Mock policy**: MSW no boundary; `renderWithProviders`; não mockar hooks internos. Gerar PDF: o teste cobre o comportamento do passo 6 contra handlers MSW (200/202/400) — **não** invocar download real (assertar a chamada/URL).

### 1. RED — testes primeiro
#### `_components/__tests__/onboarding-cta.test.tsx`
- [ ] `is_staff=false` → CTA ausente (null).
- [ ] `is_staff=true` → CTA visível; clique abre o wizard (Dialog presente).

#### `tenant-lease-onboarding/__tests__/success-step.test.tsx`
- [ ] "Concluir" chama `onClose`.
- [ ] "Gerar PDF" com handler `{pdf_path}` → dispara download (assertar URL `/download?path=` ou chamada equivalente).
- [ ] Handler `202 {task_id}` → mensagem "processando" (sem falso sucesso).
- [ ] Handler `400` (sem locador) → `toast.error` PT.

#### Regressão `contract-generate-modal`
- [ ] Continua funcionando com `{pdf_path}` (união não quebra o consumidor atual); `202` não vira falso sucesso.

> Rodar (devem falhar):
> ```bash
> cd frontend && npx vitest run "app/(dashboard)/_components/__tests__/onboarding-cta.test.tsx" \
>   "app/(dashboard)/_components/tenant-lease-onboarding/__tests__/success-step.test.tsx" \
>   "app/(dashboard)/leases"
> ```

### 2. GREEN — implementar CTA, success-step, união do hook, ajuste do modal, montagem no dashboard, handlers MSW.

### 3. REFACTOR — DRY
- Extração do caminho relativo do PDF (`contracts/`/`media/`) reaproveitada do `contract-generate-modal` (mover p/ util se duplicar).
- Discriminação `"pdf_path" in result` num único helper se usada em 2 lugares.

### 4. VERIFY — gate (escopo desta sessão) + e2e manual
```bash
cd frontend
npx vitest run "app/(dashboard)/_components/__tests__/onboarding-cta.test.tsx" \
  "app/(dashboard)/_components/tenant-lease-onboarding" \
  "app/(dashboard)/leases"   # regressão do modal/contrato
npm run type-check
npx eslint "app/(dashboard)/_components/onboarding-cta.tsx" \
  "app/(dashboard)/_components/tenant-lease-onboarding" \
  "app/(dashboard)/page.tsx" lib/api/hooks/use-leases.ts \
  "app/(dashboard)/leases/_components/contract-generate-modal.tsx" tests/mocks/handlers.ts
```
**E2E manual (smoke, documentar no SESSION_STATE)**: backend rodando (`runserver`) + frontend (`npm run dev`), logar como admin → dashboard → "Novo inquilino + contrato" → criar (novo e existente) → gerar PDF (com locador cadastrado) e verificar download; sem locador → mensagem 400 PT.

---

## Constraints
- CTA e campos admin gated por `is_staff`. Passo 6 trata `{pdf_path}`/`202`/`400` (sem polling — YAGNI).
- União discriminada em `useGenerateContract` **sem** quebrar `contract-generate-modal` (atualizar o consumidor).
- Reusar a extração de path/`/download` existente; toasts PT via `getErrorMessage`.
- Sem `eslint-disable`/`@ts-ignore`/`as`/`!` em produção; sem barrel/re-export.

## Critérios de Aceite (binários)
- [ ] CTA "Novo inquilino + contrato" no dashboard, visível só p/ `is_staff`, abre o wizard.
- [ ] Passo 6: "Concluir" fecha; "Gerar PDF" baixa (`{pdf_path}`), trata `202` (mensagem, sem falso sucesso) e `400` sem locador (toast PT).
- [ ] `useGenerateContract` é união discriminada; `contract-generate-modal` atualizado e em regressão verde.
- [ ] Todos os testes verdes; `type-check` 0 erros; `eslint` 0 erros/0 warnings; sem suppressions.
- [ ] E2E manual (novo + existente + PDF) documentado no SESSION_STATE.

## Handoff
1. Gate verde + e2e manual.
2. Atualizar `prompts/SESSION_STATE.md`: feature **CONCLUÍDA** (web); resumo end-to-end; nota de que o **app mobile (Plano 2)** reusa o endpoint `POST /api/onboarding/tenant-lease/`.
3. Rodar `/audit` contra os Critérios de Aceite das S51–S55 e fechar gaps.
4. Commit:
   ```
   feat(frontend): dashboard CTA + onboarding PDF step (eager/202/400) + e2e polish

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. Feature web encerrada. **Plano 2 (mobile)** será desenhado quando a sessão de installments/payroll terminar — reusa o endpoint transacional desta feature.
