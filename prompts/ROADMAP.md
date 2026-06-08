# Roadmap de Implementação — Módulo Financeiro

## Grafo de Dependências

```
                    ┌──────┐
                    │  01  │  Models + Migration
                    └──┬───┘
                ┌──────┴──────┐
                ▼             ▼
            ┌──────┐      ┌──────┐
            │  02  │      │  06  │  CashFlowService
            └──┬───┘      └──┬───┘
          ┌────┴────┐        │
          ▼         ▼        ▼
      ┌──────┐  ┌──────┐ ┌──────┐
      │  03  │  │  04*  │ │  07  │  DashboardService
      └──┬───┘  └──┬───┘ └──┬───┘
         │      ┌──┘        │
         ▼      ▼           │
      ┌──────┐              │
      │  05*  │             │
      └──┬───┘              │
         │      ┌───────────┘
         ▼      ▼
      ┌──────────┐
      │    08    │  SimulationService + Endpoints
      └────┬─────┘
           ▼
      ┌──────────┐
      │    09    │  Frontend Schemas + Hooks
      └────┬─────┘
           ▼
      ┌──────────┐
      │    10    │  Navegação + Base Pages
      └────┬─────┘
      ┌────┼────────┐
      ▼    ▼        ▼
  ┌──────┐┌──────┐┌──────┐
  │  11  ││  12  ││  13  │
  └──┬───┘└──┬───┘└──┬───┘
     │       │       │
     └───┬───┘       │
         ▼           │
      ┌──────┐       │
      │  14  │◄──────┘  (usa padrão de chart do 13)
      └──┬───┘
         ▼
      ┌──────┐
      │  15  │  Permissões + E2E + Polish
      └──────┘

  * 03, 04, 05 são sequenciais entre si (modificam os mesmos arquivos:
    core/viewsets/financial_views.py e core/urls.py)
```

---

## Waves

### Wave 1 — Fundação
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **01** | Models + Migration + Tests | nenhuma |

> Um trabalhador. Tudo depende dos models.

---

### Wave 2 — Camada Core (paralela)
| Sessão | Descrição | Dependência | Arquivos |
|--------|-----------|-------------|----------|
| **02** | Serializers + Tests | 01 | `core/serializers.py` |
| **06** | CashFlowService + Tests | 01 | `core/services/cash_flow_service.py` (novo) |

> **Paralelo**: 02 e 06 dependem apenas de 01 e não compartilham arquivos.
> 02 trabalha na camada de serialização, 06 na camada de serviços.

---

### Wave 3 — APIs Simples + Dashboard Service (paralela)
| Sessão | Descrição | Dependência | Arquivos |
|--------|-----------|-------------|----------|
| **03** | ViewSets Simples (Person, Card, Category, Settings) | 02 | `core/viewsets/financial_views.py` (novo), `core/urls.py` |
| **07** | FinancialDashboardService + Tests | 06 | `core/services/financial_dashboard_service.py` (novo) |

> **Paralelo**: 03 depende de 02 (serializers), 07 depende de 06 (CashFlowService).
> Não compartilham arquivos — um cria viewsets, outro cria service.

---

### Wave 4 — APIs Complexas (sequencial)
| Sessão | Descrição | Dependência | Arquivos |
|--------|-----------|-------------|----------|
| **04** | Expense + Installment ViewSets | 02, 03 | `core/viewsets/financial_views.py`, `core/urls.py` |
| **05** | Income, RentPayment, Employee ViewSets | 02, 03 | `core/viewsets/financial_views.py`, `core/urls.py` |

> **Sequencial obrigatório**: 04 e 05 modificam os mesmos arquivos (`financial_views.py` e `urls.py`).
> 04 antes de 05 por prioridade (despesas são mais críticas que receitas).

---

### Wave 5 — Simulação + Endpoints de Dashboard/CashFlow
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **08** | SimulationService + Dashboard/CashFlow endpoints | 05, 06, 07 |

> Precisa de todos os services (06, 07) e que as URLs estejam registradas (03-05).
> Cria `simulation_service.py` (novo) e `financial_dashboard_views.py` (novo).

---

### Wave 6 — Frontend Foundation
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **09** | Schemas Zod + API Hooks + MSW | 08 (backend completo) |

> Precisa de todos os endpoints do backend prontos para definir types e MSW handlers.
> A partir daqui, todo o trabalho é frontend.

---

### Wave 7 — Navegação + Base
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **10** | Sidebar expandível + Persons, Categories, Settings | 09 |

> Modifica `sidebar.tsx` e `constants.ts` (navegação).
> As páginas seguintes dependem da navegação existir.

---

### Wave 8 — Páginas CRUD (paralela)
| Sessão | Descrição | Dependência | Diretório |
|--------|-----------|-------------|-----------|
| **11** | Página de Despesas (smart form, drawer) | 10 | `financial/expenses/` |
| **12** | Income + RentPayments + Employees | 10 | `financial/incomes/`, `rent-payments/`, `employees/` |
| **13** | Dashboard Financeiro (6 widgets) | 10 | `financial/_components/`, `financial/page.tsx` |

> **Paralelo**: Cada sessão cria arquivos em diretórios separados.
> Nenhuma modifica arquivos compartilhados. Todas dependem apenas de 10 (navegação) e 09 (hooks).

---

### Wave 9 — Simulador
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **14** | Simulador com cenários e gráficos comparativos | 13 (referência de chart), 09 (hooks) |

> Depende do 13 como referência de padrão de gráfico (CashFlowChart).
> Cria todos os arquivos em `financial/simulator/` (sem conflito).

---

### Wave 10 — Finalização
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **15** | Permissões + E2E Tests + Export + Polish | todas |

> Modifica ViewSets (permissions), páginas (conditional UI), export hook.
> Testa tudo de ponta a ponta.

---

### Wave 11 — Correções Pós-Auditoria (sequencial)
| Sessão | Descrição | Dependência | Gaps cobertos |
|--------|-----------|-------------|---------------|
| **16** | Backend: Correções críticas + gaps de serviço | 15 | #1,2,3,4,6,7,8 |
| **17** | Frontend: Schemas, hooks e interfaces corrigidos | 16 | #5,9,10,11,12,16 |

> Sequencial: 17 depende das correções backend de 16.

---

### Wave 12 — Novas Páginas (paralela parcial)
| Sessão | Descrição | Dependência | Gaps cobertos |
|--------|-----------|-------------|---------------|
| **18** | Página de Pagamentos a Pessoas + PersonSummaryCards | 17 | #13,14,15 |
| **19** | Controle Diário de Entradas e Saídas | 17 | Nova funcionalidade |

> **Paralelo**: 18 e 19 criam páginas em diretórios diferentes.
> Ambas dependem de 17 (hooks corrigidos).

---

### Wave 13 — Polish Final
| Sessão | Descrição | Dependência |
|--------|-----------|-------------|
| **20** | PersonIncome page + Testes E2E + Polish | 18, 19 |

> Verifica tudo, testa tudo, fecha todos os gaps restantes (#16).

---

## Resumo Visual (Atualizado)

```
Wave    Sessões                     Trabalhadores    Duração
────    ───────                     ─────────────    ───────
  1     [01]                              1          1 sessão
  2     [02] + [06]                       2          1 sessão
  3     [03] + [07]                       2          1 sessão
  4     [04] → [05]                       1          2 sessões
  5     [08]                              1          1 sessão
  6     [09]                              1          1 sessão
  7     [10]                              1          1 sessão
  8     [11] + [12] + [13]               3          1 sessão
  9     [14]                              1          1 sessão
 10     [15]                              1          1 sessão
 11     [16] → [17]                       1          2 sessões
 12     [18] + [19]                       2          1 sessão
 13     [20]                              1          1 sessão
                                                    ─────────
                                          Total:    15 sessões
                                          (vs 20 sessões sequencial)
```

**Economia**: 5 sessões (~25%) com paralelismo nas Waves 2, 3, 8 e 12.

## Cobertura de Gaps

| Gap | Sev | Sessão | Descrição |
|-----|-----|--------|-----------|
| 7 | Crítico | 16 | SyntaxError simulation_service.py |
| 1 | Médio | 16 | Fixed expenses com pessoa no person_summary |
| 2 | Médio | 16 | end_date no Expense |
| 3 | Baixo | 16 | utility_bills is_offset filter |
| 4 | Médio | 16 | Projeção parcelas is_offset filter |
| 6 | Baixo | 16 | category_breakdown is_offset filter |
| 8 | Baixo | 16 | Simulação base exclui offsets |
| 5 | Alto | 17 | PersonSummary interface corrigida |
| 9 | Alto | 17 | CashFlowMonth interface corrigida |
| 10 | Alto | 17 | expense.schema.ts is_offset |
| 11 | Alto | 17 | person-payment.schema.ts criado |
| 12 | Alto | 17 | use-person-payments.ts hook |
| 16 | Médio | 17 | use-person-incomes.ts hook |
| 13 | Alto | 18 | Página PersonPayments |
| 14 | Alto | 18 | PersonSummaryCards atualizado |
| 15 | Alto | 18 | is_offset toggle no expense form |

**16/16 gaps cobertos. Zero pendentes.**

---

## Caminho Crítico

O caminho mais longo (determina duração mínima):

```
01 → 02 → 03 → 04 → 05 → 08 → 09 → 10 → 11* → 14 → 15
                                           12*
                                           13*
```

**11 passos sequenciais** no caminho crítico (waves 1-10).
Na Wave 8, qualquer das 3 sessões (11/12/13) pode ser o gargalo — são independentes.

---

## Notas para Execução Paralela

### Usando Git Worktrees (recomendado)
```bash
# Wave 2: duas sessões em paralelo
git worktree add ../financial-serializers -b feat/financial-serializers   # Sessão 02
git worktree add ../financial-cashflow -b feat/financial-cashflow         # Sessão 06
# Ao final: merge ambas em master

# Wave 3: duas sessões em paralelo
git worktree add ../financial-viewsets -b feat/financial-viewsets         # Sessão 03
git worktree add ../financial-dashboard-svc -b feat/financial-dashboard-svc  # Sessão 07

# Wave 8: três sessões em paralelo
git worktree add ../financial-expenses-page -b feat/financial-expenses-page   # Sessão 11
git worktree add ../financial-income-pages -b feat/financial-income-pages     # Sessão 12
git worktree add ../financial-dashboard-ui -b feat/financial-dashboard-ui     # Sessão 13
```

### Usando Sessões Claude Code Nomeadas
```bash
# Wave 2 paralela
claude -n "session-02-serializers"    # Terminal 1
claude -n "session-06-cashflow"       # Terminal 2

# Wave 8 paralela
claude -n "session-11-expenses"       # Terminal 1
claude -n "session-12-income"         # Terminal 2
claude -n "session-13-dashboard"      # Terminal 3
```

### Resolução de Conflitos entre Waves
- **Wave 2→3**: Sem conflitos (arquivos diferentes)
- **Wave 3→4**: 03 cria `financial_views.py`, 04 e 05 adicionam a ele — merge trivial (append)
- **Wave 4→5**: 05 é a última a tocar `urls.py` antes de 08 — 08 cria arquivo novo
- **Wave 8**: Sem conflitos (diretórios isolados)

---

# Roadmap — Feature: Calendário de Controle de Aluguéis (Dashboard)

**Design Doc**: `docs/plans/2026-06-02-rent-payment-calendar-design.md`
**Branch**: `feat/rent-payment-calendar`
**Status**: feature **web concluída** (sessões 21–25). Reaproveita `RentPayment`/`FeeCalculatorService`/`DateCalculatorService` — sem novo model/migration.

## Cadeia (estritamente sequencial: 21 → 22 → 23 → 24 → 25)

```
21  Backend: RentScheduleService + refactor DRY do DailyControlService + unit tests
 ▼
22  Backend: endpoints rent_calendar + toggle_rent_payment + integration tests
 ▼
23  Frontend: data layer (use-rent-calendar optimistic + query-keys + MSW) + hook tests
 ▼
24  Frontend: UI (5 componentes grid date-fns + montagem no dashboard) + component tests
 ▼
25  Refator late-payments-alert → toggle unificado + remoção de mark_rent_paid + /audit
```

> **Sequencial obrigatório**: cada sessão depende da anterior. `mark_rent_paid` (backend) e
> `useMarkRentPaid` (web) são deliberadamente mantidos até a Sessão 25 para que todas as
> sessões intermediárias permaneçam verdes (sem estado de árvore inválido).

| # | Sessão | Status |
|---|--------|--------|
| 21 | `RentScheduleService` + refactor DRY `DailyControlService` | concluída |
| 22 | endpoints `rent_calendar` + `toggle_rent_payment` | concluída |
| 23 | hooks `use-rent-calendar` (optimistic) + query-keys + MSW | concluída |
| 24 | UI (5 componentes + montagem no dashboard) | concluída |
| 25 | refator consumidor web → toggle unificado + remover `useMarkRentPaid` (web) + audit | concluída |

## Item futuro escopado (fora desta feature)

| Item | Bloqueio | Pré-requisito |
|------|----------|---------------|
| Migração do consumidor **mobile** (`mobile/lib/api/hooks/use-admin-actions.ts` + `mobile/app/(admin)/actions/mark-paid.tsx`) de `mark_rent_paid` → `toggle_rent_payment`, seguida da remoção do action backend `mark_rent_paid` | A Sessão 25 escolheu a **saída (B)**: mantém `mark_rent_paid` (backend) + consumidor mobile intactos, pois o app `mobile/` é um consumidor vivo **fora do escopo do design doc** e **inverificável** (sem `type-check`/`lint`/test runner em `mobile/package.json`). | Emendar o design doc (§2/§4.3/§8) para escopar o mobile **e** configurar verificação em `mobile/package.json` (`type-check`/`lint`/test runner). Só então uma sessão dedicada migra o mobile e remove `mark_rent_paid` do backend. |

---

# Roadmap — Feature: App Mobile Completo (Responsivo + PWA + Offline + Web Push)

**Design Doc**: `docs/plans/2026-06-04-mobile-pwa-offline-design.md`
**Branch**: `feat/mobile-pwa-offline`
**Status**: prompts 26–33 escritos/revisados (crítico de consistência: zero divergências de contrato). Nenhuma sessão executada.

## Grafo de Dependências

```
   FRONTEND                         BACKEND
   ┌──────┐                         ┌──────┐
   │  26  │ fundações responsiv.    │  31  │ model WebPushSubscription
   └──┬───┘                         └──┬───┘
   ┌──┴───┐                            ▼
   ▼      ▼                         ┌──────┐
┌──────┐┌──────┐                    │  32  │ sender dual-channel + endpoints
│  27  ││  28  │ manifest+ícones    └──┬───┘
└──────┘└──┬───┘                       │
  cards    ▼                           │
        ┌──────┐                       │
        │  29  │ Serwist SW            │
        └──┬───┘                       │
       ┌───┴───┐                       │
       ▼       ▼                       │
   ┌──────┐  ┌──────┐◄─────────────────┘
   │  30  │  │  33  │ Web Push UI (precisa de 29 + 32)
   └──────┘  └──────┘
   offline
```

## Waves

| Wave | Sessões | Paralelismo | Observação |
|------|---------|-------------|------------|
| 1 | **26** (FE) + **31** (BE) | 2 trabalhadores | stacks diferentes, sem conflito |
| 2 | **27** + **28** (FE) + **32** (BE) | 3 trabalhadores | 27 e 28 não compartilham arquivos (data-table vs manifest/layout); 32 depende de 31 |
| 3 | **29** (FE) | 1 | depende de 28 (manifest) |
| 4 | **30** (FE) | 1 | depende de 29 (SW p/ shell offline) |
| 5 | **33** (FE) | 1 | depende de **29 (sw.ts) + 32 (endpoints)** |

**Caminho crítico**: `26 → 28 → 29 → 33` (com `32` pronto antes de `33`). `30` ramifica de `29`. Backend `31 → 32` corre em paralelo ao frontend.

## Conflitos de arquivo (atenção em execução paralela)

- `app/layout.tsx`: criado/editado por **26** (viewport) e **28** (themeColor + appleWebApp) → **sequencial 26 antes de 28**.
- `app/sw.ts`: criado por **29**, apenas **anexado** por **33** → 29 antes de 33.
- `core/models.py` (31), `core/services/notification_service.py` + `core/viewsets/__init__.py` + `core/urls.py` (32) → 31 antes de 32.
- `27` (data-table) e `28` (manifest/ícones/layout) tocam arquivos distintos → seguros em paralelo após 26.


---

# Roadmap - Feature: Modulo Financeiro do Condominio (Saidas, Saldo, Reserva, Distribuicao)

**Design Doc**: `docs/plans/2026-06-06-condominium-finance-design.md` (v3)
**Sessoes**: 34-50 (17) - **Branch sugerida**: `feat/condo-finance`
**Status**: prompts escritos (34-50) + revisao de consistencia aplicada. **S34 concluída** (Fase 1a — fundação `finances` + `core.Condominium` + `Building.condominium` faseada + helper TZ + gate ampliado; branch `feat/condo-finance`). S35–50 pendentes.

## Grafo de dependencias (fases sec.14 do design)

```
1a 34  app finances + Condominium + Building.condominium + gate ampliado + TZ + factories   -- MAIOR RISCO PROD
        |
   +----+-------------------------------+
   v                                    v
1b 35 forms owner/salary/prepaid        Fase 2 BE: 36 models -> 37 services+cache -> 38 serializers/viewsets/calendar
   (so core; paralelo a 36)                                          |
                                                                     v
                                              Fase 2 FE: 39 data layer -> 40 calendario+contas UI
Fase 3 (apos 36/37): 41 installment/employee models+services -> 42 api -> 43 frontend
Fase 4 (apos 37):    44 reserve/income/close models -> 45 balance/close services+api -> 46 frontend
Fase 5 (apos 45):    47 projection/simulation backend -> 48 frontend
Fase 6 (apos 45/48): 49 owner distribution backend -> 50 frontend + e2e/polish
```

Cadeia: 34 -> (35 || 36); 36->37->38->39->40; 41->42->43; 44->45->46; 47->48; 49->50. Modelos antes de servicos antes de serializers/viewsets antes de frontend.

## Contratos cross-session AUTORITATIVOS (se um prompt divergir, ISTO prevalece)

- **Owner = NAO-INVASIVO**: `owner=null`=condominio; sem mudanca no income SSOT, sem migracao de owner (design sec.6/sec.17; PROD confirmado).
- **`Bill` fontes (FKs nullaveis)**: S36 cria so `Bill.billing_account`; **S41** adiciona `Bill.installment` (+unique `(installment)`) **e** `Bill.employee` (+unique `(employee, competence_month)`) via `add_field` - `Installment`/`Employee` nascem na **S41** (Fase 3). NAO em S44.
- **`BillPaymentService.pay`/`unpay`**: base **caixa** na **S37**; extensao `funded_from=reserve` (-> `ReserveMovement(withdrawal, bill=...)` + guarda de saldo) **e** guard `assert_open` de mes fechado = **S45**. S44 e models-only e NAO toca `pay()`.
- **Cache cross-app**: receivers que invalidam `finance-*` em escritas de `Apartment`/`Apartment.owner`/`Lease`/`RentPayment`/`FinancialSettings`/`RentAdjustment`/`MonthSnapshot`(finalize/rollback) = **S37** (prefixos `finance-dashboard`/`finance-cash-flow`/`finance-projection` num bloco unico). `combined_calendar` fica **sem cache**.
- **Calendario combinado (S38 = fonte)**: dia tem `rent_entries` (entradas) e `bill_exits` (saidas); frontend (S39/S40) consome esses nomes verbatim.
- **Projecao (S47 = fonte)**: por mes `year`/`month`/`income_total`/`expenses_total`/`net`/`cumulative_cash`/`is_actual`/`is_closed` (Decimais string); frontend (S48) consome `net`/`cumulative_cash` verbatim.
- **`formatMonthYear`** produz **"Junho de 2026"** (com " de ", nao barra).
- **RLS**: toda tabela nova do `finances` habilita RLS na **mesma migracao** (PROD tem RLS em todas as publicas via 0047; `.claude/rules/database.md`). Policy/escopo por condominio = futuro (design sec.15).
- **Gate ampliado (S34)**: `--cov=finances` + coverage source + pyright include + `mypy core/ finances/`; **>=90% standalone em `finances`** nas fases backend.
- **TZ**: helper unico `America/Sao_Paulo` (`finances/services/timezone.py`, S34) para "hoje/mes atual".
- **Wedge (S45)**: incluir teste de wedge com **termos mistos** (a-receber/a-pagar pendentes + transferencia de reserva simultaneos) - design sec.4.2.

## Waves
| Wave | Sessoes | Paralelo |
|------|---------|----------|
| 1 | 34 | fundacao sozinha |
| 2 | 35 || 36 | 35 (FE, so core) || 36 (BE models) |
| 3 | 37 -> 38 | apos 36 |
| 4 | 39 -> 40 | Fase 2 frontend |
| 5 | 41 -> 42 -> 43 | Fase 3 |
| 6 | 44 -> 45 -> 46 | Fase 4 |
| 7 | 47 -> 48 | Fase 5 |
| 8 | 49 -> 50 | Fase 6 |

> **Execucao recomendada**: estritamente sequencial 34->50 (gate 100% + >=90% em `finances` por fase antes de avancar - design sec.16 / feedback_quality_gate). Paralelismo so na wave 2 (35||36) se desejado.

---

# Roadmap — Feature: Fluxo "Novo inquilino + contrato" (web)

**Design Doc**: `docs/plans/2026-06-07-tenant-lease-onboarding-design.md`
**Sessões**: 51–55 (5) · **Branch sugerida**: `feat/tenant-lease-onboarding` (a partir de `master`)
**Status**: prompts escritos (51–55). Nenhuma sessão executada. **Plano 2 (mobile) é posterior** (após a sessão de installments/payroll terminar) e reusa o endpoint transacional desta feature.

## Grafo de dependências

```
51 BE root fixes (disponibilidade apto + captura dependentes/auditoria + guard locador)
   |
   v
52 BE endpoint transacional POST /api/onboarding/tenant-lease/ (service + serializer + view + rota)
   |                                   53 FE extração DRY (derivações/date/resident-dependent +
   |                                      remoção email/phone_alternate)  [paralelo a 51/52]
   +-------------------+-------------------+
                       v
                  54 FE wizard combinado + useOnboardTenantLease + schema  (precisa 52 + 53)
                       |
                       v
                  55 FE CTA dashboard + passo PDF (eager/202/400) + e2e/polish/audit
```

Cadeia: `51 → 52`; `53` independente (FE, paralelo); `54` depende de **52 + 53**; `55` depende de **54** (e do guard da 51).

## Waves
| Wave | Sessões | Paralelo | Observação |
|------|---------|----------|------------|
| 1 | **51** (BE) ‖ **53** (FE) | 2 trabalhadores | stacks diferentes, sem conflito de arquivo |
| 2 | **52** (BE) | 1 | depende de 51 |
| 3 | **54** (FE) | 1 | depende de 52 (contrato API) + 53 (utils) |
| 4 | **55** (FE) | 1 | depende de 54 |

> **Caminho crítico**: `51 → 52 → 54 → 55`. `53` corre em paralelo (não bloqueia até a 54).

## Contratos cross-session AUTORITATIVOS (se um prompt divergir, ISTO prevalece)
- **Endpoint**: `POST /api/onboarding/tenant-lease/` (admin-only). Body `{ tenant{...,id?}, lease{... SEM responsible_tenant_id/tenant_ids}, resident_dependent{name,phone,cpf_cnpj?}? ⊕ resident_dependent_id? }`. 201 `{ tenant, lease }`. Erros `400 {tenant:{...}}`/`400 {lease:{...}}` (apto → `lease.apartment`); `403`/`401`. Servidor injeta `responsible_tenant_id`/`tenant_ids`.
- **S51 fornece**: `LeaseSerializer.validate` rejeita apto ocupado (`{"apartment": ["Este apartamento já possui um contrato ativo."]}`); `TenantSerializer.create/update` setam `tenant._created_dependents` (ordem do array) + propagam auditoria; `prepare_contract_context` levanta `ValidationError` PT sem locador → `generate_contract` 400.
- **S52 fornece**: `TenantOnboardingService.onboard` (`@transaction.atomic`, `select_for_update` no `Apartment`, `except IntegrityError`→400 `apartment`).
- **S53 fornece**: `@/lib/utils/lease-derivations` (`deriveRentalValue`,`deriveDueDayFromStartDate`); `@/lib/utils/date` (`parseLocalDate`); `@/lib/schemas/lease.schema` (`leaseValuesSchemaShape`); `@/app/(dashboard)/_components/shared/resident-dependent-field`; **email/phone_alternate removidos** do domínio do inquilino.
- **S54 fornece**: `TenantLeaseOnboardingWizard` props `{open,onOpenChange,onSuccess(tenant,lease)}`; `useOnboardTenantLease` → `{tenant,lease}`; prefill converte `furnitures`→`furniture_ids` (NÃO usar `useUpdateTenant`).
- **S55 fornece**: `useGenerateContract` união discriminada `{pdf_path} | {task_id,status}` (consumidor `contract-generate-modal` atualizado); CTA gated `is_staff`; passo 6 trata 200/202/400.
- **Sem migração/RLS** (nenhum model novo). **Sem regra "1 contrato ativo por inquilino"** (constraint de apto + filtro do front).
- **Gate por sessão** (memória `feedback_testing_scope` + `coding-standards`): rodar testes só nos arquivos editados + regressão dirigida; BE `ruff`+`mypy core/`+`pyright`; FE `type-check`+`eslint`; zero erros/warnings; sem suppressions.
