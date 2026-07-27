# Sessão 79 — `ThirdPartyStatementService`: extrato por pessoa com FIFO computado

**Fase 2 (terceiros) — sessão 3 de 6.** Backend puro. O coração da fase.

Design: `@docs/plans/2026-07-27-condo-third-party-payments-design.md` §6.

Depende de: S77 (modelo), S78 (caixa).

## Contexto

- **Design (ler §6 inteiro)**: `@docs/plans/2026-07-27-condo-third-party-payments-design.md`
- **Padrão de prompts/TDD**: `@prompts/00-prompt-standard.md`
- **Regras**: `CLAUDE.md`, `.claude/rules/architecture.md` (serviço stateless), `.claude/rules/coding-standards.md`

### Exemplares (arquivo:linha)

| Padrão | Local | Por quê |
|--------|-------|---------|
| **Serviço de extrato (o mais próximo)** | `finances/services/account_statement_service.py` (`AccountStatementService.build`) | Forma do serviço, shape do retorno, e o **fix de N+1 da S67** (pré-carregar antes do loop) |
| **Agregação por mês sem loop** | `finances/services/condo_balance_service.py:335-346` (`_caixa_outflow`) | `Sum` + `or ZERO`; nunca somar em Python |
| **`quantize_money` na fronteira** | `finances/services/condo_balance_service.py` (`result_of_month`, `:87-89`) | Decimal em toda a cadeia, quantize só ao retornar |
| **Mês atual / timezone** | `core/services/timezone.py` (`today_sp`) | Nunca `date.today()` |
| **Subquery de valor pago** | `finances/models.py:149-165` (`_open_balance_paid_subquery`) | Guardas `payment__is_deleted=False` — replicar a disciplina |

## A regra em uma frase

> Alocação FIFO cronológica de um pool único de acertos sobre o devido mês a mês — **computada a cada leitura, jamais persistida**.

Não persistir é decisão de arquitetura, não detalhe: permite corrigir lançamento retroativo sem migração de dados nem sujeira de alocações órfãs. É o modelo do *family loans* que o usuário já opera.

## Arquivos

- **Criar**: `finances/services/third_party_statement_service.py`
- **Criar**: `tests/unit/test_finances/test_third_party_statement_service.py`

## Escopo

### `ThirdPartyStatementService.build(person_id, today) -> ThirdPartyStatement`

**Retorno é `TypedDict`, não `dict` cru**, e dinheiro sai via `money_str` (`finances/money.py`) — convenção da casa para exatamente esta forma. Exemplar direto: `AccountStatementService.build(account_id, today) -> AccountStatement` (`account_statement_service.py:183`), com os `TypedDict`s `StatementStats`/`StatementMonthRow`/`StatementPlanRow` (`:33/:39/:53`). `dict` cru brigaria com `mypy --strict`/`pyright` quando o viewset indexar o resultado — e ambos são gate.

**NÃO cachear.** O extrato depende de `today_sp()`; virada de meia-noite não é escrita, então cache nunca invalidaria. Precedentes explícitos: `month_board` (`dashboard_views.py:310-312`) e o próprio `AccountStatementService` ("read-only, uncached").

#### 1. Devido do mês

```
devido(M) = Σ Payment.amount  (funded_from=THIRD_PARTY, paid_by=P, payment_date em M, vivos)
          + Σ Bill.amount_total (paid_by_person=P, competence_month=M, lifecycle_state != CANCELED, vivos)
```

- Pagamentos agrupam por `payment_date`; compras por `competence_month` (= mês em que cai no cartão da pessoa).
- `amount_total` **sempre** via `Bill.objects.with_amounts(today)` — nunca somar `BillLineItem` em Python (§4.4 do design anterior).
- Compra parcelada: cada parcela é sua própria `Bill` com competência própria → cai no mês certo sem lógica extra.
- Bills `CANCELED` fora; `SUSPENDED`/`DEFERRED` **dentro** (a dívida com a pessoa existe independentemente do estado da conta).

**Performance:** duas agregações ORM com `values("<campo>").annotate(Sum(...))` — uma para pagamentos, uma para compras. **Proibido** loop com query por mês (o precedente `owedByMonthRange` da referência existe justamente porque a versão ingênua fazia centenas de queries). Teste de contagem de queries obrigatório: constante para 2 e para 12 meses.

#### 2. Janela de meses

Do primeiro mês com movimento até `max(mês atual, último mês com movimento)`. Meses sem movimento **dentro** da janela aparecem com `devido = 0` (senão o extrato tem buracos). Pessoa sem nada → `months: []` e totais zerados, **não** erro.

#### 3. FIFO (função pura, sem I/O)

Implementar como função module-level pura recebendo listas já buscadas — testável isoladamente, espelhando `allocate-payments.ts` da referência:

```
pool = Σ todos os acertos da pessoa (pool único; a data do acerto não amarra a mês)
para cada mês em ordem cronológica:
    devido = devido(M)
    se devido < 0:  pool += abs(devido); fillable = ZERO   # crédito propaga adiante
    senão:          fillable = devido
    aplicado  = min(pool, fillable)
    pool     -= aplicado
    resto     = fillable - aplicado
    se M <= mês atual: total_em_aberto += resto            # mês futuro não conta
    se M <  mês atual: total_atrasado  += resto
saldo_credor = pool restante
```

#### 4. Status (derivado, nunca coluna)

| Status | Regra |
| --- | --- |
| `credit` | `devido < 0` |
| `paid` | `resto == 0` e `devido > 0` |
| `overdue` | `resto > 0` e mês < mês atual |
| `partially_paid` | `aplicado > 0`, `resto > 0`, mês atual/futuro |
| `open` | `aplicado == 0`, `resto > 0`, mês atual/futuro |

Ordem de avaliação importa: `credit` antes de tudo; `paid` antes de `overdue`.

#### 5. Retorno

```python
{
  "person_id": int, "person_name": str,
  "months": [{"month": "YYYY-MM-01", "devido": str, "aplicado": str,
              "resto": str, "status": str,
              "items": [{"kind": "payment"|"purchase", "id": int,
                         "description": str, "amount": str, "date": "YYYY-MM-DD"}]}],
  "totals": {"total_devido": str, "total_pago": str, "total_em_aberto": str,
             "total_atrasado": str, "saldo_credor": str},
}
```

Decimais **string** (contrato do módulo). `quantize_money` só na fronteira. `today_sp()` para "mês atual".

## TDD

Red primeiro. Cenários obrigatórios (calcular à mão, nunca contra a própria fórmula):

1. Cada um dos 5 status isoladamente
2. **Overpayment vira crédito do mês seguinte**: deve 1000, acerta 1500 → mês `paid`, seguinte já abatido em 500
3. **Crédito antes de mês vencido propaga adiante**: mês com `devido < 0` seguido de mês positivo → abate mesmo sem acerto real
4. **Mês futuro com resto não conta** em `total_em_aberto` nem `total_atrasado`, mas aparece em `months` como `open`
5. Pagamento e compra **no mesmo mês** somam
6. Bill `CANCELED` não entra; `SUSPENDED`/`DEFERRED` entram
7. Compra parcelada 10× → 10 meses com uma parcela cada
8. Pessoa sem movimento → `months: []`, totais zerados, sem erro
9. Acerto soft-deletado sai do pool
10. Pagamento de terceiro de **outra** pessoa não vaza para o extrato
11. Sequência realista: compra → acerto parcial → compra → acerto total → saldo zero
12. Meses sem movimento no meio da janela aparecem com `devido = 0`
13. **Contagem de queries constante** (2 meses vs 12 meses)
14. Precisão: valores com centavos que não somam redondo (ex.: 3 parcelas de 33,33 sobre 100,00)

## NÃO fazer

- **Não** persistir alocação (sem model, sem coluna, sem cache de resultado).
- **Não** criar API/serializer/viewset (S80) nem frontend (S81/S82).
- **Não** alterar `condo_balance_service` (S78 já fechou) nem models (S77).
- **Não** somar dinheiro em Python quando o ORM pode agregar.

## Aceite

- Rodada escopada verde: `python -m pytest tests/unit/test_finances/test_third_party_statement_service.py --cov-fail-under=0`
- **Cobertura ≥95% do serviço novo**, medida com comando explícito:
  `python -m pytest tests/unit/test_finances/test_third_party_statement_service.py --cov=finances.services.third_party_statement_service --cov-fail-under=95`
  Para isso ser atingível, o serviço **não pode ter branches defensivas inalcançáveis** (ex.: `except Person.DoesNotExist` — a validação de pessoa é da S80, no viewset, não aqui).
- Suíte `finances` completa sem regressão (é aqui que o gate de 90% do `pytest.ini` se aplica)

> **Atenção ao `addopts`:** `pytest.ini` embute `--cov-fail-under=90` sobre `core`+`finances`. Rodada escopada sem `--cov-fail-under=0` falha mesmo com todos os testes passando.
- `ruff` + `mypy core/ finances/` + `pyright` zerados
- `makemigrations --check` → "No changes detected"
