# Módulo Financeiro — Lessons Learned & Knowledge Base

**Implementado em:** Março 2026 (20 sessões + correções)
**Design Doc:** `docs/plans/2026-03-21-financial-module-design.md`
**Prompts de sessão:** `prompts/01-backend-models.md` a `prompts/20-person-income-page-polish-tests.md`
**Estado das sessões:** `prompts/SESSION_STATE.md`
**Dados iniciais:** `scripts/data/financial_data_template.json` + `scripts/import_financial_data.py`

---

## 1. Contexto do Negócio

O condomínio é familiar (2 prédios: 836 e 850 + sítio), gerido pela sogra/sogro do Alvaro (dev). A receita vem dos aluguéis dos kitnets, mas as dívidas estão distribuídas em cartões de crédito e empréstimos nos nomes dos filhos (Rodrigo, Tiago, Junior) e genro (Alvaro). A Camila (filha/esposa do Alvaro) administra o condomínio.

### Pessoas e Papéis

| Pessoa | Relação | Cartões | Recebe | Papel |
|--------|---------|---------|--------|-------|
| Rodrigo | Filho | 3 (Itau Azul, Itau Visa, Caixa) | R$1.100 estipêndio | Carrega dívidas |
| Tiago | Filho | 1 (placeholder) | Aluguel kitnets 101, 103/836 | Proprietário + carrega dívidas |
| Alvaro | Genro | 3 (Trigg, Players, Samsung) | Aluguel kitnets 200, 203/836 | Dev + proprietário + carrega dívidas |
| Junior | Filho | 0 | R$1.100 estipêndio | Carrega empréstimos (Placas Solar R$950/mês) |
| Camila | Filha | 3 (Nubank, Renner, Mercado Pago) | Implícito (admin) | Administradora, compras nos cartões dela são pagas pelo condomínio |
| Rosa | Funcionária | 0 | R$800 fixo + variável | Mora no kitnet 206/850 (aluguel compensado) |

### Regras de Negócio Especiais

- **Sistema "pagar para morar"**: inquilino paga dia X para morar de X a X+1mês
- **Aluguel pré-pago**: Kitnet 113/836 pago até 29/09/2026 (R$20.700 antecipado, recalculado por mudança de kitnet)
- **Salary offset**: Kitnet 206/850 — aluguel da Rosa compensado no salário
- **Descontos (is_offset)**: Compras nos cartões que são para os sogros/Camila, subtraídas do total da pessoa. Ex: Carro Camila R$3.034/mês no cartão do Alvaro, com R$1.534 de desconto (parte dela)
- **Água 836 suspensa**: Faturas não pagas, esperando DMAE cortar para negociar parcelamento
- **IPTU**: 9 parcelamentos ativos (4 no 836, 5 no 850) com parcelas de valor variável (correção monetária)
- **2 relógios de luz no 836**: Um principal (Av. Circular 840), um secundário (Av. Circular 836) que será desligado

---

## 2. Arquitetura do Módulo Financeiro

### Models (core/models.py, linhas 783-1082)

```
Person → CreditCard (1:N)
Person → PersonIncome (1:N) — o que tem direito a receber
Person → PersonPayment (1:N) — pagamentos efetivos recebidos
Person → EmployeePayment (1:N) — pagamento de funcionário

Expense → ExpenseInstallment (1:N)
Expense → Person (FK opcional)
Expense → CreditCard (FK opcional)
Expense → Building (FK opcional)
Expense → ExpenseCategory (FK opcional)

ExpenseCategory → ExpenseCategory (self FK, subcategorias)

Income — receitas extras (aposentadoria, avulsos)
RentPayment — pagamentos de aluguel recebidos
FinancialSettings — singleton (saldo inicial)
```

### Campos Especiais no Expense

| Campo | Uso |
|-------|-----|
| `is_installment` | True para parcelados (gera ExpenseInstallments) |
| `is_debt_installment` | True para parcelamento de dívida negociada (água/luz/IPTU) |
| `is_recurring` | True para gastos fixos mensais (Internet, ração, etc.) |
| `is_offset` | True para descontos — subtraído do total da pessoa |
| `is_paid` | Para despesas não-parceladas |
| `end_date` | Data fim para gastos fixos recorrentes |
| `expected_monthly_amount` | Valor projetado para gastos fixos |
| `recurrence_day` | Dia do mês para gastos fixos |

### Campos Especiais em Outros Models

| Model.Campo | Uso |
|------------|-----|
| `Apartment.owner` | FK para Person — kitnets com owner não são receita do condomínio |
| `Lease.prepaid_until` | Aluguel pré-pago até esta data |
| `Lease.is_salary_offset` | Aluguel compensado como salário |
| `ExpenseCategory.parent` | FK self para subcategorias |

### Services (core/services/)

| Service | Responsabilidade |
|---------|-----------------|
| `CashFlowService` | Fluxo de caixa mensal, projeção 12 meses, resumo por pessoa |
| `FinancialDashboardService` | Visão geral, dívida por pessoa/tipo, parcelas vencendo/vencidas |
| `SimulationService` | Cenários "e se" (quitar antecipado, mudar aluguel, etc.) |
| `DailyControlService` | Controle diário (entradas/saídas por dia, saldo acumulado) |
| `FeeCalculatorService` | Cálculos de multa, tag fee (pré-existente) |

### Endpoints Financeiros (/api/)

```
CRUD: persons, credit-cards, expense-categories, expenses, expense-installments,
      incomes, rent-payments, employee-payments, person-incomes, person-payments,
      financial-settings

Dashboard: financial-dashboard/{overview,debt_by_person,debt_by_type,
           upcoming_installments,overdue_installments,category_breakdown}

Cash Flow: cash-flow/{monthly,projection,person_summary,simulate}

Daily: daily-control/{breakdown,summary,mark_paid}
```

### Frontend Pages (frontend/app/(dashboard)/financial/)

| Página | Rota | Função |
|--------|------|--------|
| Dashboard | `/financial` | 6 widgets (saldo, gráfico 12 meses, resumo pessoa, parcelas, alertas, categorias) |
| Despesas | `/financial/expenses` | CRUD com smart form, filtros, drawer de parcelas, toggle is_offset |
| Receitas | `/financial/incomes` | CRUD com filtros |
| Pgto Aluguel | `/financial/rent-payments` | CRUD com filtros cascata prédio→apto |
| Funcionários | `/financial/employees` | Pagamento mensal (fixo + variável + offset) |
| Pessoas | `/financial/persons` | CRUD com seção inline de cartões |
| Categorias | `/financial/categories` | CRUD hierárquica com indentação |
| Configurações | `/financial/settings` | Singleton (saldo inicial) |
| Simulador | `/financial/simulator` | 6 cenários, gráfico comparativo |
| Pgto Pessoas | `/financial/person-payments` | Controle de pagamentos a cada pessoa |
| Recebimentos | `/financial/person-incomes` | Quem recebe o quê (estipêndio/aluguel) |
| Controle Diário | `/financial/daily` | Timeline dia a dia, saldo diário |

---

## 3. Armadilhas e Cuidados

### is_offset — SEMPRE filtrar

Toda query que soma despesas para o condomínio DEVE ter `is_offset=False`. Offsets são descontos pessoais, não despesas reais. Se esquecer o filtro, as despesas ficam infladas.

Locais que filtram: `_collect_card_installments`, `_collect_loan_installments`, `_collect_utility_bills`, `_collect_one_time_expenses`, `_collect_fixed_expenses`, `_get_projected_expenses`, `get_overview`, `get_debt_by_person`, `get_debt_by_type`, `get_upcoming_installments`, `get_overdue_installments`, `get_expense_category_breakdown`, `_get_projected_utility_average`.

### PersonIncome — Filtrar por datas

Estipêndios e aluguéis de pessoa devem ser filtrados por `start_date` e `end_date`. `_collect_person_stipends` recebe `month_start` e filtra `.filter(start_date__lte=month_start).exclude(end_date__lt=month_start)`.

### Gastos fixos — end_date

`_collect_fixed_expenses` exclui gastos com `end_date < month_start`. Se `end_date` é null, projeta indefinidamente.

### PersonPayment.reference_month — Dia 1 obrigatório

O `PersonPaymentSerializer` valida que `reference_month.day == 1`. O `get_person_summary` busca por `reference_month=month_start` onde `month_start = date(year, month, 1)`. Se o dia não for 1, o pagamento nunca será encontrado.

### FinancialSettings — Singleton com fallback

Usar `FinancialSettings.objects.first()` com fallback para `Decimal("0.00")`. Nunca `get(pk=1)` que pode dar `DoesNotExist`.

### Parcelas de valor variável — parcelas_detalhadas

IPTU e dívidas negociadas têm parcelas com valores diferentes (correção monetária). Usar `parcelas_detalhadas` no JSON com cada parcela explícita, em vez de `valor_parcela` fixo.

### Contas de consumo com parcelamento incluso

Faturas de luz/água podem incluir parcela de dívida negociada (ex: Luz 850 inclui R$629,35/mês de parcelamento). O campo `parcelamento` no JSON vincula à entrada em `parcelamentos_divida`. O CashFlowService trata esses como categorias separadas (`utility_bills` vs `debt_installments`).

### except em Python 3.14

Python 3.14 (PEP 758) muda a semântica de `except A, B:` — agora significa "catch A, assign to B". Usar `except ObjectDoesNotExist:` (base class Django) em vez de `except (Apartment.DoesNotExist, Lease.DoesNotExist):` que o ruff reformata para sintaxe diferente.

### Ruff target-version

Usar `py313` (não `py314`) no `pyproject.toml` — ruff ainda não suporta py314.

---

## 4. Script de Importação (scripts/import_financial_data.py)

### Como usar

```bash
# Simular (não grava)
python scripts/import_financial_data.py scripts/data/financial_data_template.json --dry-run

# Importar
python scripts/import_financial_data.py scripts/data/financial_data_template.json

# Reimportar do zero
python scripts/import_financial_data.py scripts/data/financial_data_template.json --clear-first
```

### Convenções do JSON template

- `parcela_atual = 0`: compra nova, 1ª parcela na próxima fatura
- `parcela_atual = -1`: carência 60 dias
- `parcela_atual > 0`: parcela sendo paga agora
- `data_proxima_parcela`: âncora para calcular datas (data da parcela_atual)
- `data_compra`: data original (alternativa ao data_proxima_parcela)
- `_comentario`: entradas com esse campo são ignoradas (marcadores visuais)
- `suspensa: true`: conta não importada (ex: água 836 esperando corte)

### Parser de faturas

`scripts/parse_itau_fatura.py` — parseia texto de faturas Itaú para formato JSON do template.

---

## 5. Categorias

5 categorias principais + subcategorias:

| Principal | Subcategorias |
|-----------|--------------|
| Pessoal | Saúde, Mercado, Farmácia, Vestuário |
| Carros | Gasolina, Pedágio, Manutenção Veículo |
| Kitnets | Manutenção, Material de Construção, Internet, Faxinas |
| Camila | (sem subcategorias) |
| Ajuda | (sem subcategorias — empréstimos entre familiares) |

---

## 6. Migrations

```
0001-0011: Models base (Building, Apartment, Tenant, Lease, etc.)
0012: Módulo financeiro (10 models + campos em Apartment/Lease)
0013: ExpenseCategory.parent (subcategorias)
0014: Expense.is_offset (descontos)
0015: PersonPayment (pagamentos a pessoas)
0016: Expense.end_date (data fim gastos fixos)
```

---

## 7. Melhorias Pendentes

- **Parcelas Próximas**: Agrupar por cartão/pessoa em vez de mostrar parcela por parcela (134 itens)
- **Parser de faturas**: Expandir para Nubank, Caixa, Renner, Mercado Pago (hoje só Itaú)
- **Saldo diário**: Verificar se DailyControlService está funcionando corretamente no frontend
- **PersonSummaryCards**: Verificar erro "Erro ao carregar resumo por pessoa" — backend funciona, erro pode ser CORS/auth
- **Tiago**: Cartão não cadastrado (placeholder) — adicionar quando tiver fatura
- **Dados do banco**: Kitnets desalugados que já estavam no banco antes do import (203/836, 212/836, 214/836, 206/850) — verificar se são reais
- **Conta de luz sítio**: Valor aproximado R$200, confirmar valor real
- **Internet sítio**: R$200, confirmar
