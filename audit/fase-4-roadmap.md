# Fase 4 — Roadmap de Features (2026-07-13)

Base factual: infraestrutura JÁ existente — PaymentProof lifecycle completo (falta só UI web), Twilio WhatsApp integrado (OTP), push Expo/WebPush, tipos de notificação `admin_notice`/`rent_adjustment` declarados e nunca emitidos, IPCAIndex + RentAdjustmentService com alertas de elegíveis, endpoint PIX do tenant, export client-side (use-export), scripts/backup_db.py, Bill.attachment (campo morto), month-close/reserve/distribution sem export.

Mercado 2026 (fontes no relatório): sistemas BR para locação convergem em cobrança via WhatsApp com baixa automática, PIX instantâneo, reajuste IGPM/IPCA automático, assinatura digital com prova de aceite, e relatório anual pronto para IR; segmento small-landlord internacional (TenantCloud/Innago/MagicDoor) padronizou rent collection online + screening + portal do inquilino a US$15-75/mês.

## Matriz impacto × esforço

| # | Feature | Impacto | Esforço | Justificativa ancorada | Prioridade |
|---|---------|---------|---------|------------------------|------------|
| 1 | **Tela web de moderação de comprovantes PIX** | 5 | 1 | Backend 100% pronto (proof_views + aprovação→RentPayment da Fase 2); sem ela o fluxo do inquilino termina num beco; "baixa de pagamento" é o recurso central dos sistemas BR | **P1** |
| 2 | **Régua de cobrança WhatsApp com PIX embutido** | 5 | 3 | "Envio de cobrança direto pelo WhatsApp e baixa automática" é O recurso de mercado BR 2026 (Imobia, comparativos Pilota); Twilio + payload PIX + crons já existem — é composição, não construção | **P2** |
| 3 | **Reajuste IPCA em lote + notificação ao inquilino** | 4 | 2 | Reajuste automático por índice é padrão BR; alertas de elegíveis já existem, aplicar é 1-a-1 hoje; tipos `rent_adjustment`/`adjustment_eligible` declarados e mortos | **P3** |
| 4 | Composer de avisos (admin_notice) + central de notificações web | 4 | 2 | Portal promete "Comunicados do condomínio"; tipo declarado morto; push pronto; sino do header segue morto (U10) | P4 |
| 5 | Relatório anual de rendimentos (IR) por proprietário/imóvel | 4 | 2 | Citado literalmente como diferencial nos comparativos BR ("pronto para declaração"); todos os dados existem em RentPayment/finances | P5 |
| 6 | Exports no finances/ (prestação de contas condominial) | 3 | 1 | Único módulo sem export; use-export client-side pronto; prestação de contas é obrigação recorrente | P6 |
| 7 | Assinatura eletrônica do contrato (Autentique/Clicksign) | 4 | 4 | Padrão de mercado BR com "prova de envio e aceite" para litígios; hoje contrato é PDF impresso | P7 |
| 8 | Anexo de fatura/comprovante em Bill (campo morto) | 3 | 2 | Bill.attachment existe sem UI; validators de upload prontos; **depende do storage durável (I2/S3)** | P8 |
| 9 | Backup self-service na UI (download + agendado) | 2 | 2 | Só CLI local hoje; risco operacional | P9 |
| 10 | Trilha de auditoria por registro (history) | 2 | 3 | AuditMixin só guarda último updated_by | P10 |

## Top 3 — especificação técnica resumida

### 1. Moderação de comprovantes (web) — esforço ~1 sessão
- **Dados**: nenhum modelo novo. `GET /api/admin/proofs/?status=pending` já existe (proof_views, IsAdminUser) + review action.
- **Telas**: `app/(dashboard)/proofs/page.tsx` — lista com filtro por status, preview do arquivo (proof file endpoint), aprovar/rejeitar com motivo; badge de pendentes no sidebar; push `proofs` do sw.ts passa a apontar para a rota (hoje cai na home).
- **Riscos**: preview de arquivo em prod depende de storage efêmero (I2) — arquivos podem ter sumido; exibir estado "arquivo indisponível".

### 2. Régua de cobrança WhatsApp + PIX — esforço ~2-3 sessões
- **Dados**: `CollectionMessageLog` (lease, reference_month, kind: reminder/due/overdue, sent_at, channel, status) para idempotência e prova de envio. Template de mensagem em FinancialSettings (ou constante versionada).
- **Backend**: estender `send_scheduled_notifications` (cron já no render.yaml): para cada lease cobrável (SSOT RentScheduleService), enviar WhatsApp via serviço Twilio existente com valor efetivo + código PIX (endpoint tenant PIX já gera payload) + link do portal; respeitar rent_tracking_start_date e meses pagos; log + retry simples.
- **Riscos**: custo/limite Twilio; opt-out do inquilino (flag por lease); não cobrar prepago/salary-offset (SSOT já cobre — Fase 2).
- **Telas**: aba "Cobranças" no dashboard (histórico por mês + reenviar manual).

### 3. Reajuste IPCA em lote — esforço ~1-2 sessões
- **Dados**: nenhum modelo novo (RentAdjustment existe).
- **Backend**: action `rent-adjustments/apply_batch/` (lista de lease_ids → aplica via RentAdjustmentService em transação, retorna sucessos/falhas por item); emitir `Notification(rent_adjustment)` ao inquilino no apply (tipo já declarado).
- **Telas**: página de alertas de reajuste ganha seleção múltipla + "Aplicar selecionados" com preview do novo valor (índice acumulado); toast com resumo.
- **Riscos**: idempotência (não aplicar 2× no mesmo aniversário — service já valida); comunicação obrigatória ao inquilino (lei exige aviso — a notificação cobre).
