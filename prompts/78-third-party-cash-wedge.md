# Sessão 78 — Caixa e wedge: o acerto sai, o pagamento de terceiro não

**Fase 2 (terceiros) — sessão 2 de 6.** Backend puro. **A sessão mais sensível da fase: altera fórmula monetária.**

Design: `@docs/plans/2026-07-27-condo-third-party-payments-design.md` §5 (caixa) e §5.1 (wedge).

Depende de: S77 (`ThirdPartySettlement`, `FundedFrom.THIRD_PARTY`, `Payment.paid_by`).

## O invariante em uma frase

> Pagamento de terceiro quita a conta **sem** tirar dinheiro do caixa. O acerto com a pessoa **tira**.

## O que JÁ funciona (verificado — não mexer)

- `CondoBalanceService._caixa_outflow` (`finances/services/condo_balance_service.py:335-346`) filtra `payment__funded_from=FundedFrom.CAIXA` — **allowlist**. `third_party` já é excluído automaticamente. **Não alterar essa função.**
- `Bill.objects.with_amounts` soma `PaymentAllocation` sem olhar `funded_from` → a conta é quitada normalmente. Correto.
- Nenhum outro ponto trata `Payment` como saída de caixa (`condo_month_close_service`, `dashboard_views`, `condo_projection_service`, `condo_simulation_service`, `condo_calendar_service` não referenciam `Payment`).

**A tentação a resistir:** "adicionar suporte a third_party no `_caixa_outflow`". Não. A allowlist já resolve. Qualquer edição ali é regressão.

## O que muda

### 1. `settlements_out` no `_Components`

Novo componente: Σ `ThirdPartySettlement.amount` do mês por `settlement_date`, vivos (`is_deleted=False`, manager default já cobre).

**Sem filtro de condomínio** — igual a `_caixa_outflow` e `_reserve_movement_sum`. `_components(year, month, building_id)` não recebe condomínio; o serviço é mono-condomínio por construção. **Não** inventar lookup de condomínio nem mudar a assinatura.

Seguir o padrão dos componentes existentes (`_caixa_outflow`, `_reserve_movement_sum`) — agregação ORM (`Sum`), `or ZERO`, **nunca** soma em Python.

**`building_id`: zerar quando filtrado.** Precedente exato a copiar — `condo_balance_service.py:296-305`, que faz o mesmo para transferências de reserva:

```python
# Reserve transfers are condo-level (no building) — only in the condo-wide view.
reserve_to_cash = ZERO
deposit_out = ZERO
if building_id is None:
    ...
```

**O motivo correto** (não é só "não tem prédio"): `settlements_out` **cancela** nos dois lados da identidade do wedge, exatamente como `deposit_out`/`reserve_to_cash`. Por isso zerá-lo é seguro — o resíduo continua 0,00. Comentar isso no código; um implementador que interprete "não tem prédio ⇒ zera" como regra geral vai aplicá-la onde **não** cancela.

**Consequência a registrar (não é bug, é limite):** uma compra de terceiro **pode** ter prédio, e entra em `expense_competence` filtrado por prédio — mas o acerto correspondente nunca entra. Logo **caixa por prédio não é figura conciliável com banco**; só a visão condo-wide é. Documentar no docstring.

### 2. `cash_change_of_month`

```python
cash_out = comp.caixa_outflow + comp.deposit_out + comp.settlements_out
```

Atualizar a docstring (hoje documenta a fórmula explicitamente).

### 3. `_wedge_residual` — a parte delicada

```python
delta_payables = comp.expense_competence - comp.caixa_outflow - comp.settlements_out
```

**Por quê:** a compra de terceiro entra em `expense_competence` (é `Bill` ativa) e não em `caixa_outflow` — já balanceado, igual a uma conta não paga. Mas o acerto é saída de caixa **sem** despesa de competência correspondente (a despesa foi reconhecida quando a compra virou `Bill`). Sem esse termo, `wedge_ok` fica vermelho num mês com acerto.

Atualizar a docstring de `_wedge_residual` explicando o termo novo.

## TDD

Red primeiro. **Nenhum teste pode usar float.** Testes obrigatórios:

1. Pagamento de terceiro **não** altera `cash_change_of_month` (baseline == depois)
2. Pagamento de terceiro **quita** a bill (`amount_remaining == 0`) — prova que os dois efeitos coexistem
3. Acerto **reduz** `cash_change_of_month` exatamente pelo valor
4. Acerto soft-deletado volta a não contar
5. `cash_balance` reflete o acerto no mês seguinte
6. **`wedge_ok` verde** num mês com compra de terceiro + acerto simultâneos (o teste-chave da sessão)
7. `wedge_ok` verde num mês só com compra (sem acerto)
8. `wedge_ok` verde num mês só com acerto (sem compra)
9. `settlements_out == ZERO` quando `building_id` é passado
10. `CondoMonthClose.close` congela `cash_balance_end` já com o acerto descontado
11. Regressão: mês sem nada de terceiro → todos os números idênticos ao baseline

Comparar sempre contra valores calculados à mão no teste, nunca contra a própria fórmula do serviço.

## Arquivos

- **Modificar**: `finances/services/condo_balance_service.py`
- **Criar**: `tests/unit/test_finances/test_third_party_cash_impact.py`

## NÃO fazer

- **Não** alterar `_caixa_outflow`.
- **Não** alterar `with_amounts` nem nenhuma annotation de `Bill`.
- **Não** criar serviço de extrato (S79), API (S80) nem frontend (S81/S82).
- **Não** tocar `CondoMonthCloseService` (ele já consome `cash_balance`; se um teste indicar o contrário, **parar e reportar** antes de editar).

## Aceite

- Rodada escopada verde: `python -m pytest tests/unit/test_finances/test_third_party_cash_impact.py --cov-fail-under=0` (sem a flag o comando falha mesmo com tudo verde — `pytest.ini` embute `--cov-fail-under=90` sobre `core`+`finances`)
- **Suíte `finances` completa sem regressão** (esta sessão mexe em dinheiro: rodar tudo, não só o escopo) — é aqui que o gate de 90% vale
- `ruff` + `mypy core/ finances/` + `pyright` zerados
- `makemigrations --check` → "No changes detected" (esta sessão não cria migration)
