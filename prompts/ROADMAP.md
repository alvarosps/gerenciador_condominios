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
