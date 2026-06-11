# Plano P8.1 — Roadmap de features (ondas) — gates de brainstorming + infra a reusar

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P8 (features novas — nivel de mercado jun/2026) · **Branch sugerida:** por feature (`feat/<slug>`, ex.: `feat/pix-conciliation-asaas`) · **Depende de:** P0–P2 concluidos (base segura/correta de dinheiro e dados)

## Objetivo

Este NAO e um plano de fix — e o roadmap acionavel das features novas que levam o sistema ao nivel de mercado de junho/2026 para o locador solo. Lista 20 features em 4 ondas (must-have, diferenciadores, IA, futuro/condicional), cada uma com o problema que resolve, a INFRA EXISTENTE a reusar (confirmada lendo o codigo), PSP/lib/custo quando aplicavel, prioridade, complexidade e o gate obrigatorio. **Cada feature so vira codigo apos passar pelo gate: `/brainstorming` (architecture gate Django/DRF) → design doc em `docs/plans/` → prompts TDD numerados em `prompts/NN`.** A Onda 1 itens 1–4 (conciliacao PIX, cockpit fiscal Carne-Leao/IRPF, regua de cobranca, assinatura eletronica) sao os de maior ROI e devem ser priorizados.

## Achados endereçados

Roadmap de features — nao remedia achados de auditoria (esses estao em P0–P7). A tabela abaixo mapeia cada feature ao gap de mercado que ela fecha.

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| FEAT | Conciliacao manual de PIX (PaymentProof aprovado a mao) nao escala e gera inadimplencia | core/viewsets/proof_views.py:89-99 · core/models.py:1684 (PaymentProof) | QR dinamico por lease/mes (txid) + webhook PSP da baixa automatica no RentPayment |
| FEAT | Locador PF nao tem apoio fiscal (Carne-Leao mensal + DARF + informe anual) | core/models.py:1313 (RentPayment) · 1543 (MonthSnapshot) · finances Expense | Cockpit fiscal: base tributavel − deducoes, lembrete DARF, informe por imovel/CPF |
| FEAT | Cobranca de atraso e manual e tardia (so calculo de multa sob demanda) | core/services/fee_calculator.py:50 (calculate_late_fee) · core/management/commands/send_finance_alerts.py | Regua D-3/D0/D+1/D+5 via cron reusando Notification/DeviceToken/WhatsApp |
| FEAT | Assinatura de contrato e presencial/papel (gera contrato mas nao assina) | core/views.py:359 (generate_contract) | Assinatura eletronica (gov.br/ZapSign) acoplada ao fluxo de geracao |
| FEAT | Inquilino nao tem recibo nem portal completo (so paga e envia comprovante) | core/views.py:359 · core/viewsets/tenant_views.py | Recibo PDF automatico + portal do inquilino completo no app |
| FEAT | Vistoria entrada/saida e informal (sem termo, sem fotos) | core/models.py:310 (Furniture) · 1684 (PaymentProof upload) | Vistoria digital: checklist+fotos+termo PDF |
| FEAT | Manutencao nao tem fluxo (chamado → fornecedor → custo) | finances Bill/Expense | Central de manutencao: chamado vira Expense/Bill |
| FEAT | Sem P&L por unidade (rentabilidade liquida por kitnet) | finances/models.py (CondoMonthClose) | Inverter o fechamento para yield liquido por unidade |
| FEAT | Inquilino nao ve transparencia do condominio | finances dashboard (read-only) | Resumo read-only do fechamento no app |
| FEAT | Sem score de pontualidade do inquilino | core/models.py:1313 (RentPayment historico) | Score de pontualidade derivado do historico |

## Abordagem técnica

Roadmap, nao implementacao. A "abordagem" e o **processo de gate por feature** + as **tabelas de onda**. Nenhuma linha de codigo aqui — cada feature e um mini-projeto proprio.

### Processo de gate (obrigatorio, identico para toda feature)

1. **`/brainstorming`** (carregar TAMBEM o `/brainstorming` do projeto, com architecture gate Django/DRF): definir o problema, o escopo minimo (YAGNI), as fronteiras de integracao (PSP/LLM/gov.br), o modelo de dados (novos models herdam `AuditMixin`+`SoftDeleteMixin` salvo excecao justificada; dinheiro em `DecimalField(max_digits=12, decimal_places=2)` + `quantize` 2 casas), as camadas (Views→Services→Models; serializer dual pattern read-nested/`_id`-write), e a estrategia de teste (mockar SO fronteiras externas).
2. **Design doc** em `docs/plans/AAAA-MM-DD-<slug>-design.md` (mesmo padrao dos designs existentes: `2026-06-06-condominium-finance-design.md`, `2026-06-08-condo-utility-bills-parser-iptu-design.md`). Deve fechar: contratos de API (request/response), migrations (com RLS na mesma migration que cria tabela — padrao `core/migrations/0047`/`0048`; `RunSQL ENABLE ROW LEVEL SECURITY` com `reverse_sql`, SQL estatico), invalidacao de cache (signals para os novos models), permissoes (`FinancialReadOnly`/`IsAdminUser`/`IsTenantOrAdmin` de `core/permissions.py`), e o lado frontend (hook TanStack Query, schema Zod, pagina).
3. **Prompts TDD numerados** em `prompts/NN-<slug>-<fase>.md` (a numeracao atual vai ate `prompts/64`; novas features comecam em **`prompts/65`** — conferir `prompts/SESSION_STATE.md` antes). Seguir o `/prompt-writing` do projeto (TDD Red→Green→Refactor→Verify, context engineering, exemplar index) e executar com `/prompt-session` + `/audit`.
4. **Branch por feature** (`feat/<slug>`), PR por feature. Backup antes de qualquer migrate (`python scripts/backup_db.py`).

> Direcao de dependencia em TODA feature: services novos do dominio condominial vivem em `finances/services/` (o substituto NOVO); o legado pessoal do core (`Person/Expense/RentPayment/cash-flow/daily-control/financial-dashboard` + `app/(dashboard)/financial/`) e DEPRECATED — features novas NAO devem depender dele nem estende-lo. `core` NAO importa `finances` (inversao proibida; comandos de dominio finances vivem em `finances/management/commands/`).

### Onda 1 — must-have (baseline de mercado 2026) — **MAIOR ROI: itens 1–4**

| # | Feature | Problema que resolve | Infra existente a reusar | PSP/lib/custo | Prioridade | Complexidade |
|---|---|---|---|---|---|---|
| 1 | **Conciliacao PIX automatica** | Baixa manual de PaymentProof nao escala; atraso na conciliacao | `RentPayment` (`core/models.py:1313`, ja com `unique_active_rent_payment` por lease+mes); `PaymentProof` (`:1684`) vira **fallback** quando o webhook nao chega; `FeeCalculatorService.calculate_late_fee` (`core/services/fee_calculator.py:50`) para a multa embutida no valor cobrado; `resolve_pix_recipient` (apos P2.2) | **PSP Asaas** (REST + API key; taxa fixa **R$1,99/cobranca**). QR dinamico por lease/mes com `txid` unico; **webhook** de baixa que cria/atualiza o `RentPayment` do mes de referencia | **must** | **alta** |
| 2 | **Cockpit fiscal Carne-Leao + IRPF** | Locador PF sem apoio fiscal; Receita cruza PIX×DIMOB×Carne-Leao em 2026 (multa ate 75%) | `RentPayment` (receita) + `Expense`/`finances.Bill` (deducoes IPTU/condominio) + `MonthSnapshot` (`:1543`)/`CondoMonthClose` para base congelada; `Notification`/`create_notification` (`core/services/notification_service.py:32`) para lembrete DARF | Sem PSP. Relatorio mensal (base tributavel = receita − deducoes IPTU/condominio), **lembrete DARF** mensal, **informe anual** por imovel/CPF | **must** | **media** |
| 3 | **Regua de cobranca automatizada** | Cobranca manual e tardia; -30% a -60% de inadimplencia com regua | `Notification`/`DeviceToken` (`core/models.py:1646`) + `send_push_notification` (`notification_service.py:57`, ja faz Expo+WebPush); `whatsapp_service` (apos P2.2, `content_variables=json.dumps`); **cron** `send_finance_alerts` (padrao em `core/management/commands/send_finance_alerts.py`, idempotente SP-aware via `is_notification_sent_on`); `calculate_late_fee` para o valor com multa | Sem PSP novo (WhatsApp via Twilio ja integrado). Disparos **D-3 / D0 / D+1 / D+5** (D+5 com multa) | **must** | **media** |
| 4 | **Assinatura eletronica do contrato** | Contrato gerado mas assinado em papel/presencial | `generate_contract` (`core/views.py:359` → `ContractService`, PDF via `PlaywrightPDFGenerator`); acoplar pos-geracao do PDF | **gov.br** (custo-zero, assinatura avancada) OU **ZapSign API** (~**R$30/mes**). STJ validou assinatura eletronica como **titulo executivo sem testemunhas** (REsp 2.243.445/SP) | **must** | **media** |
| 5 | **Recibo PDF automatico + portal do inquilino completo** | Inquilino sem recibo e com portal incompleto | `ContractService`/`PlaywrightPDFGenerator` (mesmo pipeline de PDF) para o recibo; `RentPayment` como fonte; `core/viewsets/tenant_views.py` (portal) + app `mobile/` | Sem custo externo | diff | media |

> **Itens 1–4 sao os de maior ROI.** Item 1 e o unico de complexidade **alta** (webhook + idempotencia + reconciliacao com fallback). Itens 2–4 sao **media**. Sequencia recomendada dentro da onda: 3 (regua, reusa o cron pronto) → 1 (PIX, maior valor) → 2 (fiscal) → 4 (assinatura) → 5 (recibo/portal).

### Onda 2 — diferenciadores

| # | Feature | Problema que resolve | Infra existente a reusar | PSP/lib/custo | Prioridade | Complexidade |
|---|---|---|---|---|---|---|
| 6 | **Vistoria digital entrada/saida** | Vistoria informal, sem termo nem fotos | `Furniture` por apto (`core/models.py:310`, M2M Apartment) para o checklist; upload de arquivo no padrao `PaymentProof.file` (`:1699`, `FileField upload_to`); PDF via `PlaywrightPDFGenerator` para o termo | Sem custo externo | diff | media |
| 7 | **Central de manutencao** | Maior gap funcional vs mercado; chamado sem fluxo | Upload de foto (padrao `PaymentProof.file`); chamado fechado vira **`Expense`/`finances.Bill`** vinculado ao `Building`/`Apartment`; `Notification` para status | Sem custo externo | **diff (alto valor)** | alta |
| 8 | **P&L por unidade** | Sem rentabilidade liquida por kitnet | Inverter `CondoMonthClose`/fechamento de `finances` para **yield liquido por unidade** (receita do apto − rateio de custos) | Sem custo externo | diff | media |
| 9 | **Transparencia do condominio no app** | Inquilino nao ve fechamento | Resumo **read-only** do fechamento (`finances` dashboard) exposto no app via serializer enxuto | Sem custo externo | nice | baixa |
| 10 | **Score de pontualidade** | Sem metrica de pontualidade do inquilino | Historico de `RentPayment` (`:1313`) + datas de vencimento (`RentScheduleService`) | Sem custo externo | nice | baixa |

### Onda 3 — IA (realista para dev solo)

| # | Feature | Problema que resolve | Infra existente a reusar | PSP/lib/custo | Prioridade | Complexidade |
|---|---|---|---|---|---|---|
| 11 | **Pre-validacao de comprovante PIX (Claude vision)** | Aprovacao de PaymentProof 100% manual | `PaymentProof` (`:1684`, ja guarda `file`); fluxo de review em `proof_views.py:89-99` ganha sugestao + **aprovacao 1-clique** | **Claude Haiku 4.5** (~**R$0,01/doc**; preco US$1/US$5 por MTok input/output — confirmar em `platform.claude.com/pricing`). Mockar a fronteira HTTP da API Anthropic nos testes | diff | media |
| 12 | **Agente WhatsApp do inquilino** | Inquilino sem canal self-service | **tool-use** sobre os endpoints DRF existentes (`/api/tenant/*`); resposta na **janela 24h** do WhatsApp (gratis); `whatsapp_service` ja integrado | Claude (tool-use) + Twilio (ja integrado) | nice | alta |
| 13 | **Fallback LLM no parser DMAE/CEEE** | Parser regex quebra com layout novo da fatura | `finances/services/invoice_parsing/registry.py:42` (`detect_and_parse`) + parsers `dmae.py`/`ceee.py` (regex **primario**, mantido); LLM so quando o regex falha | Claude Haiku 4.5 (raro; so no fallback). Sem armazenar PDF (in-memory, como ja e) | nice | media |
| 14 | **Auditoria de contrato por IA (Lei 8.245/91)** | Sem verificacao juridica do contrato | Preview do template de contrato (`ContractService`); IA aponta clausulas em conflito com a Lei do Inquilinato no preview | Claude (analise de texto) | nice | media |

### Onda 4 — futuro / condicional

| # | Feature | Problema que resolve | Infra existente a reusar | PSP/lib/custo | Prioridade | Complexidade |
|---|---|---|---|---|---|---|
| 15 | **PIX Automatico** (autorizacao unica) | Cobranca recorrente sem acao do inquilino | Reusa a integracao Asaas da Onda 1 (item 1) | Obrigatorio interbancario desde **01/01/2026** (BCB Resolucao 505/2025). Condicional ao PSP suportar | nice | alta |
| 16 | **Monitor de enquadramento IBS/CBS** | Reforma tributaria; risco de enquadramento | `RentPayment` (faturamento) + contagem de imoveis (`Apartment`/`Building`) | Provavel se **>R$240k/ano + >3 imoveis**; **NFS-e a partir de ago/2026**. Condicional a regulamentacao | nice | media |
| 17 | **Submedicao de agua** | Rateio de agua sem leitura individual (reduz 20-35%) | `finances` BillingAccount agua (DMAE) + rateio por consumo lido por apto | Hardware de submedidor (fora do software). Condicional | nice | alta |
| 18 | **Deteccao de anomalia de consumo** | Sem manutencao preditiva (vazamento etc.) | Historico de faturas DMAE/CEEE (`finances.Bill`/statements) para baseline + alerta de desvio | Sem custo externo (regra estatistica lite) | nice | media |
| 19 | **Garantia/caucao + multiplos indices (IGP-M)** | `Lease` so suporta IPCA e nao modela caucao | `Lease`/`RentAdjustment` + `IPCAIndex` (estender para IGP-M); novo campo de garantia/caucao no `Lease` | Sem custo externo | nice | media |
| 20 | **Triagem de candidato (CPF+score, LGPD)** | Sem analise pre-locacao | Validadores CPF (`core/validators/`); novo fluxo de consentimento LGPD | Bureau de credito (custo por consulta). Condicional | nice | alta |

### NAO priorizar (perfil imobiliaria, nao locador solo)

CRM/funil de leads, portais Zap/OLX, white-label, multi-tenant SaaS, **DIMOB** (dispensada para PF). Fora de escopo deste roadmap — registrar como "nao fazer" para evitar scope creep.

## Arquivos a criar / modificar

Este plano (P8.1) cria/modifica APENAS documentos de planejamento. Cada feature, ao passar pelo gate, cria os seus proprios design docs e prompts.

- `docs/plans/2026-06-11-p8-1-roadmap-features-waves-plan.md` — CRIAR (este arquivo).
- `docs/plans/2026-06-11-audit-remediation-roadmap.md` — JA referencia P8.1 na linha da fase P8 (sem mudanca necessaria; opcional: trocar o link da celula "Titulo" para apontar este doc).
- Por feature (no momento do gate, NAO agora): `docs/plans/AAAA-MM-DD-<slug>-design.md` (design) + `prompts/65-<slug>-*.md`, `prompts/66-...` etc. (execucao TDD), atualizando `prompts/SESSION_STATE.md`.

**Nenhum arquivo de codigo ou de teste e tocado por este plano.** Os testes nascem dentro dos prompts TDD de cada feature (sempre primeiro o teste — Red).

## TDD — cenários de teste

Sem testes neste plano (roadmap). O que ESTE plano garante e que **cada feature carregue seus proprios cenarios TDD** no design doc + prompts, com a politica de mock do projeto (mockar SO fronteiras externas). Cenarios-chave que cada feature de Onda 1 DEVE cobrir quando for executada (registrar isso no respectivo design doc):

- **Item 1 (PIX Asaas):** webhook idempotente (mesma `txid` 2x → 1 `RentPayment`); fronteira HTTP do Asaas mockada (criar cobranca + assinatura do webhook); fallback `PaymentProof` quando webhook nao chega; multa embutida = `calculate_late_fee` cross-month; valor batendo com `effective_rental_value` (SSOT).
- **Item 2 (fiscal):** base tributavel = receita − deducoes (`is_offset=False` sempre); informe anual soma 12 meses por CPF/imovel; lembrete DARF idempotente por mes (padrao `is_notification_sent_on`).
- **Item 3 (regua):** disparo nos offsets D-3/D0/D+1/D+5 calculados com timezone SP (`today_sp`); D+5 inclui multa; idempotencia por (lease, mes, offset); nenhum disparo se ja pago (`RentPayment` existe).
- **Item 4 (assinatura):** fronteira HTTP do provedor (gov.br/ZapSign) mockada; estado do contrato (enviado/assinado) persistido; PDF assinado armazenado no padrao de storage existente.
- **Itens IA (11–14):** fronteira HTTP da API Anthropic mockada (resposta vision/tool-use canned); regex permanece o caminho primario no item 13 (LLM so no `except`).

## Migrations / dados

N/A para ESTE plano (so documentacao). Cada feature, quando executada, definira suas proprias migrations no design doc, seguindo as regras canonicas:

- Toda **tabela nova** habilita RLS na MESMA migration que a cria (`RunSQL("ALTER TABLE public.<t> ENABLE ROW LEVEL SECURITY;", reverse_sql="ALTER TABLE public.<t> DISABLE ROW LEVEL SECURITY;")`, SQL estatico — padrao `core/migrations/0047`/`0048`). RLS habilitado sem policies e o estado CORRETO (nao "corrigir").
- **Backup antes de qualquer migrate** (`python scripts/backup_db.py`); apos DDL em prod, rodar o Supabase security advisor e confirmar zero `rls_disabled`.
- Models de dinheiro em features novas: `DecimalField(max_digits=12, decimal_places=2)`, FK de historico de dinheiro com `PROTECT`/`SET_NULL` (nunca apagar lancamento real — padrao `finances.Bill`).

## Constraints (o que NÃO fazer)

- NAO escrever codigo de feature neste plano — e roadmap. Cada feature passa por `/brainstorming` → design doc → prompts ANTES de qualquer linha de codigo. **Pular o gate de brainstorming e proibido.**
- NAO construir features de perfil imobiliaria (CRM/funil, portais Zap/OLX, white-label, multi-tenant SaaS, DIMOB) — fora de escopo para locador solo.
- NAO estender nem acoplar features novas ao **modulo financeiro pessoal legado** (`Person/Expense/RentPayment-cash-flow/daily-control/financial-dashboard` + `app/(dashboard)/financial/`) — DEPRECATED; o dominio condominial novo vive no app `finances/`.
- NAO fazer `core` importar `finances` (inversao de dependencia proibida); comandos/cron de dominio finances vivem em `finances/management/commands/`.
- NAO comecar features (P8) antes de **P0–P2** concluidos (base segura e dinheiro/dados corretos) — P8 depende deles.
- NAO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `from __future__ import annotations`, TODO/FIXME nem re-exports/shims em nenhuma feature.
- NAO mockar codigo interno/ORM/services proprios nos testes das features — mockar SO fronteiras externas (HTTP do PSP/LLM/gov.br, Chrome, filesystem, tempo).
- NAO tratar como bug os falsos-positivos conhecidos: RLS habilitado sem policies (correto), `page_size` grande (intencional), avisos `rls_enabled_no_policy` do advisor (esperado).

## Critérios de aceite (binários)

- [ ] O arquivo `docs/plans/2026-06-11-p8-1-roadmap-features-waves-plan.md` existe com as 4 ondas e as 20 features tabeladas.
- [ ] Cada feature tem: problema, infra existente a reusar (com `arquivo:linha` real), PSP/lib/custo quando aplicavel, prioridade (must/diff/nice) e complexidade (baixa/media/alta).
- [ ] Esta explicito que **Onda 1 itens 1–4 sao os de maior ROI**.
- [ ] O gate por feature esta documentado: `/brainstorming` (com o do projeto) → design doc em `docs/plans/` → prompts TDD em `prompts/NN` (proxima livre = `prompts/65`).
- [ ] Custos citados: Asaas **R$1,99/cobranca**, ZapSign **~R$30/mes**, Claude Haiku 4.5 **US$1/US$5 por MTok** (~R$0,01/doc).
- [ ] Fontes citadas: Asaas docs, **STJ REsp 2.243.445/SP**, **BCB Resolucao 505/2025**, `platform.claude.com/pricing`.
- [ ] A secao "NAO priorizar" lista CRM/funil, portais, white-label, multi-tenant, DIMOB.
- [ ] Nenhum arquivo de codigo/teste foi modificado por este plano.

## Gate de verificação

Este plano e documentacao — nao ha codigo a compilar/testar. Verificacao deste doc:

```bash
# Confirmar que o arquivo existe e nenhum codigo foi tocado por este plano
git status --porcelain docs/plans/2026-06-11-p8-1-roadmap-features-waves-plan.md
git diff --name-only -- 'core/**' 'finances/**' 'frontend/**' 'mobile/**' 'tests/**'   # deve sair vazio
```

O **gate de verificacao de cada feature** (rodado quando a feature for executada, escopado nos arquivos editados + regressao dirigida; suite cheia tem flakiness pre-existente de xdist/Redis — nao e bloqueio):

```bash
# Backend
ruff check <arquivos> && ruff format --check <arquivos> && mypy core/ finances/ && pyright && python -m pytest <escopo>
# Frontend
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Zero erros E zero warnings em Ruff, mypy, Pyright, ESLint, TypeScript e pytest.

## Handoff

- Commit sugerido:
  ```
  docs(roadmap): add P8.1 features roadmap (waves) with brainstorming gates

  - 4 waves, 20 features tabeladas: must-have (PIX Asaas, fiscal Carne-Leao/IRPF,
    regua de cobranca, assinatura eletronica) + diferenciadores + IA + futuro
  - cada feature: problema, infra existente a reusar (arquivo:linha real),
    PSP/lib/custo, prioridade, complexidade e gate (brainstorming → design → prompts)
  - Onda 1 itens 1-4 = maior ROI; proxima prompt livre = prompts/65

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```
- Atualizar `docs/plans/2026-06-11-audit-remediation-roadmap.md` (opcional): linkar a celula "Titulo" da fase P8 para este doc.
- O proximo passo assumido: ao iniciar QUALQUER feature, rodar `/brainstorming` (carregando tambem o do projeto) e produzir o design doc + prompts antes de codar. A primeira feature recomendada (maior ROI/menor risco de integracao) e a **regua de cobranca (item 3)**, que reusa o cron `send_finance_alerts` ja pronto; em seguida a **conciliacao PIX Asaas (item 1)**.
- Atualizar MEMORY: nota "P8.1 roadmap de features escrito (4 ondas, 20 features, gate brainstorming→design→prompts; Onda 1 itens 1-4 = ROI; prompts comecam em 65)".
