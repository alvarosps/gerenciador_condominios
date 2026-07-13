# Roadmap de Remediação — Auditoria 2026-07-10

Fonte: `docs/plans/2026-07-10-full-audit-report.md` (~153 achados: **62 confirmados** por verificação adversarial, 87 plausíveis com verificação não concluída, 4 verificados ao vivo na UI, 1 refutado) + pendências herdadas do roadmap 2026-06-11.

**Estado da verificação:** todo o backend está confirmado com quórum (core, finances, dinheiro/timezone, segurança, cache, performance, docs, consistência de API). O bloco **[pendente-verificação]** — frontend, mobile, portal, infra, testes — não foi verificado por limite de sessão da plataforma (não por refutação); a amostragem manual pós-workflow confirmou os achados ALTA de auth do mobile. Confirmar cada item [pendente-verificação] no início da sua fase.

Convenção: cada fase vira um branch/PR focado, com gate canônico verde antes do merge (`.claude/rules/coding-standards.md`).

---

## OPS — Ações operacionais imediatas (sem código, fazer JÁ)

1. **Mergear `perf/p5-p6` no master** — P5.1/P5.2/P6.1/P6.2/P6.3 + 21 fixes de review estão prontos há um mês nessa branch local. Conferir se os 12 erros de pyright em `tests/unit/test_finances/` já estão corrigidos lá; senão, corrigir no merge.
2. **Push do master** — master local está ~11 commits à frente de `origin/master` (merge do P4 e posteriores). Backup remoto inexistente para um mês de trabalho.
3. **Deletar branches obsoletas** — `perf/frontend-bundle` (gêmea redundante do P5.2) e as branches já mergeadas (`fix/*`, `feat/condo-utility-bills`, etc.).
4. **Configurar/confirmar crons no Render** — `send_finance_alerts` e `send_scheduled_notifications` não têm agendamento versionado nem documentado; se não estiverem no dashboard do Render, os alertas de IPTU e lembretes de vencimento **nunca disparam**. Documentar no README/CLAUDE.md ou versionar `render.yaml`.
5. **Contract PDF em prod (plano 2026-06-09, Fases 2–4 abertas)** — dimensionar start command do gunicorn (`--workers 1 --threads 4 --timeout 180`) no dashboard Render; broker/worker Celery fica para P2.5 abaixo.

## P0 — Produção: dados e fluxo do inquilino (1 ALTA confirmada + bloco ALTA pendente-verificação)

- **P0.1 Storage durável para uploads** — comprovantes PIX e PDFs de contrato vivem no disco efêmero do Render com `USE_S3=False` (`condominios_manager/settings_production.py:83`): **cada deploy apaga os comprovantes enviados** (CONFIRMADO 3/3). Migrar para Supabase Storage (ou S3) + backfill do que existir.
- **P0.2 Fluxo de comprovantes web ponta a ponta** [pendente-verificação, 5 achados ALTA]:
  - Login OTP do portal web não autentica (`core/viewsets/auth_views.py:204` — verify não seta cookies nem retorna user);
  - Upload sempre 400 (`frontend/app/tenant/payments/proof/page.tsx:93` — envia `reference_month` "YYYY-MM" para DateField);
  - Sem tela de moderação no dashboard admin (backend `proof_views.review` pronto) — **tela nova, candidata a Claude Design**;
  - Aprovar comprovante não registra `RentPayment` (`core/services/proof_review_service.py:38`);
  - Lista de comprovantes enviados é useState local + backend sem endpoint de listagem para o tenant;
  - Rota `/tenant/payments/proof` órfã (sem link no nav);
  - OTP: falha do Twilio vira 500 e consome rate limit (`auth_views.py:111`).
- **P0.3 Segurança** (CONFIRMADOS, 3 achados): inquilino autenticado lê portfólio inteiro + PII de proprietários via `/api/apartments/` (`core/views.py:134`); cookie-JWT sem validação CSRF com `SameSite=None` (`core/authentication.py:22`); registro de DeviceToken permite apropriar push token de outro usuário (`core/viewsets/device_views.py:51`).

## P1 — Integridade do caixa (finances)

- **P1.1 Guard de mês fechado por `payment_date`** — `BillPaymentService.pay/unpay` (e `bulk_pay`) só checam `competence_month`; pagamento retrodatado muda o `cash_change` de mês congelado e o saldo diverge para sempre (`finances/services/bill_payment_service.py:69`; CONFIRMADO 3/3). Alinhar com `ReserveService.assert_open(movement_date)`.
- **P1.2 Demais furos de guard** (CONFIRMADOS): `IncomeEntry` destroy sem guard/update só valida data nova (`finances/viewsets/crud_views.py:748`); `generate_month/ensure_month_bills` cria contas em competência fechada (`bill_generation_service.py:68`); deletar Bill de parcela materializada órfã a parcela (`bill_generation_service.py:317`).
- **P1.3 Parcelamentos** (CONFIRMADOS): criar InstallmentPlan pela API não materializa Installments (casca inerte, `installment_payroll_views.py:32`); `convert_deferred` parcela `amount_total` em vez de `amount_remaining` (`installment_plan_service.py:110`).
- **P1.4 Reserva e agregados** (CONFIRMADOS): withdraw valida saldo agregado, não da reserva alvo (`reserve_service.py:84`); `with_amounts` confia no cascade para Payments soft-deletados (`finances/models.py:240`); visão por prédio mistura números condo-wide com filtrados (`condo_balance_service.py:123`); projeção ignora Bills futuras reais (`condo_projection_service.py:159`).

## P2 — Timezone e dinheiro no legado (6 CONFIRMADOS + relacionados)

- **P2.1** `calculate_late_fee` usa data UTC (`core/views.py:489`) — multa/status errados entre 21:00–00:00 SP e mês de referência errado na virada; usar `today_sp()` (o frontend já manda `payment_date` que o backend ignora).
- **P2.2** `calculate_due_date_change_fee` com referência UTC (`core/services/fee_calculator.py:143`) + taxa de ~1 mês cobrada quando `new_due_day == due_day` (`fee_calculator.py:150`, CONFIRMADO).
- **P2.3** `RentAdjustmentService` inteiro em UTC (`rent_adjustment_service.py:131`); `send_scheduled_notifications` em UTC (`send_scheduled_notifications.py:60`) + lembretes enviados para aluguel já pago (`:110`, CONFIRMADO). **Novo (CONFIRMADO, ALTA):** `apply_adjustment`/`get_eligible_leases` bloqueiam e ocultam reajuste de leases auto-renovadas (`rent_adjustment_service.py:57,243`) — mesma classe do bug "17/37" do calendário, contradiz o SSOT de auto-renew; o admin nunca é alertado nem consegue reajustar. Remover o guard de expiração + atualizar os 2 testes que travam o comportamento e o spec.
- **P2.6** (CONFIRMADO, ALTA-ish): `calculate_late_fee` ignora prepaid/salary-offset e usa `rental_value` cru em vez de `effective_rental_value` (`core/views.py:492`) — informa multa a quem já pagou adiantado e diverge do calendário quando há reajuste pendente.
- **P2.4** Defaults UTC persistidos no financeiro legado (`financial_views.py:200`) e "hoje" misto no dashboard (`financial_dashboard_service.py:62`); `validate_lease_dates` com `date.today()` (`model_validators.py:100`); arredondamento da última parcela em `ExpenseService.generate_installments` (`expense_service.py:93`).
- **P2.5 Celery real** — broker + worker + `CELERY_RESULT_BACKEND` (hoje ausente: ligar o broker quebraria `generate_contract`/`task_status`, `core/views.py:415` CONFIRMADO) + restaurar `sslmode=require` descartado pelo override de DATABASES (`settings_production.py:111` CONFIRMADO).

## P3 — Mobile (herdado P3.1/P3.2, agora com lista concreta — 24 achados [pendente-verificação])

O app Expo está quebrado de ponta a ponta contra o backend atual: login admin (cookie-JWT sem tokens no body, `mobile/app/login.tsx:43`), refresh quebrado que queima o token (`mobile/lib/api/client.ts:76`), deadlock de logout (`client.ts:84`), PIX lê campo inexistente (`pix.tsx:35`), criar locação 400 (dual pattern, `use-admin-properties.ts:77`), crashes em mark-paid/reajuste/detalhe-prédio, listas truncadas em 20, "marcar todas" 404, aprovação de comprovante às cegas, logout sem revogar refresh, tokens apagados ao abrir offline, deep links drifted, admin sem logout, zero gates de qualidade. Executar os planos P3.1/P3.2 de 2026-06-11 usando esta lista como critério de aceitação.

## P4 — Frontend web: correção (2 verificados ao vivo + bloco [pendente-verificação])

- **P4.1** Crash de `/financial/month-advance` (`page.tsx:107`, VERIFICADO AO VIVO) + colocar a rota no sidebar.
- **P4.2** Chaves duplicadas no `DailyTimeline` (`daily-timeline.tsx:564`, VERIFICADO AO VIVO) + `isOverdueExit` parseia `YYYY-MM-DD` com `new Date()` (vencendo-hoje vira "Atrasado", `:55`).
- **P4.3** Datas/atomicidade no expense-edit-modal: drift de dia/mês com `setMonth`+`toISOString` (`expense-edit-modal.tsx:256`) e N POSTs não-atômicos (`:232`); `payment_date` default UTC no quick-payment-modal (`:54`).
- **P4.4** Invalidations faltantes: person-payments → financial-dashboard/daily-control (`use-person-payments.ts:40`); expense/installments → daily-control (`use-expense-installments.ts:38`); terminate/transfer → dashboard (`use-leases.ts:333`).
- **P4.5** Herdados do P4.3 antigo + confirmados de novo: `parseList` por item esvazia lista inteira (~30 hooks, `use-leases.ts:31`); catch genérico engolindo erro do backend em ~28 modais; `client.ts` unwrap heurístico; `main-layout` fora do TanStack Query; fluxo dependente+lease não-atômico (`tenant-lease-modal.tsx:255`).

## P5 — UX/navegação e telas novas

- **P5.1 Navegação**: `/admin/users` órfã (`admin/users/page.tsx:28`); `MobileNav` fecha ao expandir submenu + hambúrguer duplicado (`mobile-nav.tsx:37`); sidebar não auto-expande grupo da rota ativa; sino de notificações morto no header (`header.tsx:72`).
- **P5.2 Polimentos**: ações da tabela de locações → menu kebab (8 ícones/240px); tabelas sem `overflow-x-auto` (expenses/details); "Cancelar" conta sem confirmação + rótulo "Deferir" (`bill-status-actions.tsx:61`); "até N/A" → "renovação automática"; "API Documentation" → pt-BR; consolidar/renomear grupos "Financeiro" × "Condomínio" no menu.
- **P5.3 Telas novas (candidatas a Claude Design)**: moderação de comprovantes (P0.2); composer de avisos para inquilinos (backend também não tem endpoint de composição — `notification_service.py:32`); central de notificações do admin no web; contrato do tenant sem estado falso "contrato.pdf ✓"; portal do inquilino sem locação ativa crasha (`tenant/page.tsx:73`); `/tenant/login` renderizado dentro do layout com bottom nav.

## P6 — Performance backend (11 CONFIRMADOS)

Waterfall por pessoa no dashboard legado (centenas de queries/request, `financial_dashboard_service.py:902`); projeção sem teto de meses (`financial_dashboard_views.py:187`); scan duplo de `collectible_leases` (`rent_schedule_service.py:191`); N+1 em `_build_income_summary`/`get_person_summary` (`:744`), daily-control breakdown (`:382`), `get_debt_by_person` (`:138`), `MonthAdvanceService` (`month_advance_service.py:205`), `_add_utility_notes` (`:1227`); `monthly_balance` O(n²) no finances (`dashboard_views.py:146`); índices faltando em Bill/Installment (`finances/models.py:317`); agregações em Python (daily_control).

## P7 — Cache (CONFIRMADOS, 7 achados)

`generate_installments` via bulk_create sem invalidação (`expense_service.py:117`); Tenant não invalida `finance-*` (`signals.py:86`); Lease/Apartment/Building não invalidam `financial-dashboard-*` (`signals.py:74`); invalidação fora de `transaction.on_commit` (`cache.py:187`); fallback não-Redis zera throttle counters (`cache.py:207`); versão `:1:` hardcoded (`cache.py:212`); `apps.ready()` engole falha de registro de signals (`finances/apps.py:18`).

## P8 — Testes e gates

Teste sensível a data do calendário (falha desde 01/07 — `combined-calendar-section.test.tsx`, usar `vi.setSystemTime`); 12 erros pyright em testes (conferir vs `perf/p5-p6`); mobile sem lint/type-check/testes; 26 arquivos frontend com `vi.mock` de hooks internos (herdado do P6.1, era ~8 — recontar); e2e financeiros assertam só status 200; `pytest.ini` ignora DeprecationWarning/UserWarning em bloco; mock de função interna em `test_tenant_auth_api.py:86`; fixar comportamento de `vacant_kitnets_count` com owner externo.

## P9 — Docs (CONFIRMADOS)

CLAUDE.md sem `finances/` e `mobile/`; rotas de auth documentadas inexistentes (`/api/token/`, `/api/auth/google/`); tag fee R$50/80 em `rules/financial.md` (real: R$20/40); headers de planos executados ainda "PLANEJADO" (P0–P2, P5, P6); `.env.production.example` com nomes errados de vars JWT e omissões TWILIO/VAPID; gate documentado roda mypy só em `core/` (real inclui `finances/`); `docs/STATUS.md` congelado em março; README ensinando flake8/black/isort; `tests/CLAUDE.md` com cobertura 60% (real 90%); nota sobre Chrome/PDF desatualizada.

## P10 — Herdados de 2026-06-11 ainda abertos + melhorias novas

- **Sweep `{"error"}`→`{"detail"}`** (~80 sites; coordenar com mobile em P3).
- **P4.3 deferidos**: endpoint atômico `create_with_resident` + unificação `LeaseFormModal`; tag_fee no backend; sidebar `/admin/users` (agora coberto em P5.1).
- **P7.1 Remoção do financeiro legado** — continua bloqueado por `finances/` cobrir 100% + P3; a duplicação core×finances segue sendo o maior "não faz sentido" da API/UI.
- **P8.1 Features (ondas)** — conciliação PIX, cockpit fiscal, régua de cobrança, assinatura eletrônica.
- **12 melhorias novas da auditoria** (relatório §8): destaque para aprovar-comprovante→RentPayment, composer de avisos, notificação de reajuste ao inquilino + reajuste em lote, digest diário cobrindo Bills, lista acionável de contratos vencendo, lixeira de soft-delete, import OFX/CSV, exports no finances, visão de onboarding do inquilino, backup sob demanda na UI.

---

## Pós-verificação (recomendado antes de executar as fases [pendente-verificação])

Resultado da re-verificação (2 execuções): todo o backend foi confirmado; restam 87 achados de frontend/mobile/portal/infra/testes cujos verificadores não rodaram (limite de sessão, não refutação). Apenas 1 achado refutado em ~150 (Dependent.cpf_cnpj — o normalizador de fato valida). Para fechar o bloco pendente: `Workflow resume wf_ff520369-9e7` numa janela com sessão disponível (os finders/verificadores concluídos voltam do cache; só re-rodam os ~87 restantes). Como a amostragem manual dos achados ALTA de mobile-auth se sustentou, o roadmap pode ser executado com o bloco pendente como provável — confirmando cada item no início da sua fase.
