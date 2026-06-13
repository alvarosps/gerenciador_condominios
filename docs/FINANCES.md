# Módulo Condomínio (`finances/`)

Doc consolidado do app **`finances/`** — o módulo financeiro ATUAL do condomínio (saídas/saldo/reserva/distribuição). Substitui o financeiro **pessoal** legado do `core` (Person/Expense/RentPayment), que está em depreciação (remoção em P7). O legado tem seu próprio doc: [LESSONS_LEARNED.md](LESSONS_LEARNED.md).

## Por que existe

O `core` legado misturava finanças pessoais do locador com o caixa do condomínio. O `finances/` modela só o **condomínio**: contas a pagar tipadas (água/luz/IPTU/…), parcelamentos, funcionários, reserva, receitas e o **fechamento mensal congelado**. Dependência unidirecional: **`finances` pode importar `core`; `core` NUNCA importa `finances`**.

## Modelo de dados (`finances/models.py` — 16 models)

| Model | Papel |
|---|---|
| `BillingAccount` | Conta tipada (`account_type`: water/electricity/iptu/internet/generic) + identidade (inscrição/UC/medidor/titular/endereço) + `SupplyStatus` |
| `Bill` → `BillLineItem` | Conta a pagar do mês; o dinheiro é a soma das linhas. `BillLineItem.is_offset` é armazenado **POSITIVO** e **subtraído** |
| `Payment` → `PaymentAllocation` | Pagamento e sua alocação por bill (`FundedFrom`: caixa/reserva) |
| `InstallmentPlan` → `Installment` | Parcelamento (embutido na conta de consumo, ou standalone p/ IPTU) |
| `Employee` | Funcionário (`EmployeePaymentType`: fixed/variable/mixed) |
| `Reserve` → `ReserveMovement` | Reserva (depósito/saque; `ReserveMovementKind`) |
| `IncomeEntry` | Receita do condomínio |
| `CondoMonthClose` | **Snapshot mensal congelado** (`CondoMonthCloseStatus`) — só `AuditMixin` (sem SoftDelete) |
| `BillSkip` | Marca uma conta como não cobrada num mês — só `AuditMixin` (sem SoftDelete) |
| `WaterBillStatement` / `ElectricityBillStatement` | 1:1 com `Bill` — **só leituras** (o dinheiro mora no `BillLineItem`) |
| `Category` | Categoria de conta (self-FK `parent` + `condominium`) |

`Condominium` é o **tenancy-root** e mora em **`core/models.py`** (referenciado por `finances` via FK; `Building.condominium` — migration 0048).

## Invariantes monetários

- Dinheiro do `Bill` via **`Bill.objects.with_amounts(today)`** (`amount_total`/`amount_paid`/`amount_remaining`/`payment_status`/`is_overdue` como subquery anotada) — NUNCA somado em property Python.
- `BillLineItem.is_offset` armazenado **positivo** e subtraído; quantização (`quantize_money`) só na fronteira de saída (serializer/service) — o dashboard e o `CondoMonthClose` congelado nunca diferem por 1 centavo.
- "Hoje / mês corrente" só via `core.services.timezone.today_sp()` (settings é UTC).
- Geração mensal (`BillGenerationService.ensure_month_bills`) é **idempotente e race-safe** (get_or_create nas partial-uniques + tolerância a IntegrityError).
- FKs de origem do `Bill` usam `SET_NULL` — apagar a fonte nunca apaga o histórico.

## Fechamento mensal (`CondoMonthClose`)

Snapshot imutável: ao fechar, as figuras (income_total/expenses_total/net/cash) são **congeladas no breakdown** ("frozen figures win" — o congelado vence qualquer edição posterior das bills). Invariante: o snapshot nunca difere do dashboard on-read por 1 centavo. Cuidado com reopen→close em cascata (P2.3).

## Contas tipadas + parser de fatura

Statements (água/luz) são 1:1 com a Bill e **só leituras**. O parser DMAE/CEEE roda **em memória, sem anexar o PDF** (`POST /api/finances/bills/parse_invoice/` lê → monta o rascunho → descarta o PDF). IPTU é conta-registro (não auto-gera): planos avulsos + dívida diferida; alerta IPTU = banner load-bearing + push agregado SP-aware via o cron `send_finance_alerts`.

## Permissões e RLS

- Todo o módulo é **admin-only** (`IsAdminUser` — `is_staff`/`is_superuser`); inquilino recebe 403 (P1.2).
- **RLS habilitado em toda tabela `public` nova na mesma migration** (padrão `core/migrations/0047`; migrations `finances/0004–0006`). RLS sem policy é o estado correto (o backend conecta como `postgres`, bypass).

## API — `/api/finances/` (14 routers)

`finance-categories`, `billing-accounts`, `bills`, `bill-skips`, `payments`, `installment-plans`, `installments`, `employees`, `reserves`, `reserve-movements`, `income-entries`, `condo-month-closes`, `finance-dashboard`, `finance-cash-flow`.

**Actions:** `bills/{id}/{pay,suspend}/`, `bills/{bulk_pay,generate_month,create_with_lines,parse_invoice}/`, `bills/{id}/update_with_lines/`, `condo-month-closes/{id}/{close,reopen}/`, `finance-dashboard/{overview,monthly_balance,iptu_alerts,overdue,combined_calendar,by_category,by_owner}`, `finance-cash-flow/projection`.
