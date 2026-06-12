# Roadmap de Remediação da Auditoria — 2026-06-11

> **Estado:** PLANEJADO — índice-mestre. Cada plano referenciado é um doc separado em `docs/plans/2026-06-11-pXY-*-plan.md`, executável em sequência.
> **Origem:** auditoria multi-agente completa de 2026-06-10/11 (backend, frontend, database, mobile, docs, segurança, performance) — 141 achados confirmados e verificados adversarialmente + roadmap de mercado jun/2026.

## Como usar este roadmap

1. Execute os planos **em ordem de fase** (P0 → P8). Dentro de uma fase, os planos sem dependência entre si podem rodar em paralelo (coluna "Paralelo").
2. Cada plano tem branch própria sugerida; abrir PR por plano (revisão menor, rollback fácil).
3. Antes de cada plano com migration/dado: `python scripts/backup_db.py`.
4. Gate por plano (escopado nos arquivos editados + regressão dirigida): backend `ruff check && ruff format --check && mypy core/ && pyright && python -m pytest <escopo>`; frontend `cd frontend && npm run lint && npm run type-check && npm run test:unit`. Zero erros **e** zero warnings. A suite cheia tem flakiness pré-existente (xdist/Redis) — não é bloqueio; rode regressão dirigida nos módulos tocados.
5. Ao terminar um plano, marque-o `EXECUTADO (PR #…, data)` no header do doc e atualize `prompts/SESSION_STATE.md`.

## Princípio de ordenação

Segurança e correção de dinheiro/dados primeiro (P0–P2); depois mobile (consumidor quebrado), arquitetura, performance; depois higiene (testes/docs/CI); só então **remoção do legado** (P7, exige o substituto 100% no ar); e por fim **features novas** (P8, cada uma com gate de brainstorming). Não comece P7 antes do app `finances/` cobrir todos os casos do legado.

---

## Sequência de execução

| Fase | Plano | Título | Branch | Depende de | Paralelo com |
|---|---|---|---|---|---|
| **HF — Hotfix prod** | HF-1 | 500 no PATCH /api/tenants (full_clean × dado legado) + handler global 400 + normalização marital_status | `fix/tenant-update-500-validation` | — | qualquer (bloqueia operação em prod — fazer já) |
| **P0 — Incidente** | P0.1 | Purga de PII/segredos do git + rotação + hooks + higiene | `chore/security-incident-git-purge` | — | — (fazer 1º, isolado) |
| **P1 — Segurança** | P1.1 | Servir contratos/comprovantes só autenticado | `fix/authenticated-file-serving` | P0.1 | P1.2, P1.3, P1.4 |
| | P1.2 | Segregação inquilino×admin + endpoints financeiros a `is_staff` | `fix/permission-segregation` | P0.1 | P1.1, P1.3, P1.4 |
| | P1.3 | Segurança do pipeline de template de contrato (SSTI, path traversal) | `fix/contract-template-pipeline` | P0.1 | P1.1, P1.2, P1.4 |
| | P1.4 | Hardening de auth diversos (upload, OTP, OAuth, senha) | `fix/auth-hardening` | P0.1 | P1.1, P1.2, P1.3 |
| **P2 — Dinheiro/Dados** | P2.1 | `late_fee` ciente de data real + vazamento de soft-deleted | `fix/late-fee-and-softdelete-leak` | — | P2.2, P2.3, P2.4, P2.5 |
| | P2.2 | PIX EMV (acentos/bytes) + Twilio `content_variables` | `fix/pix-emv-and-whatsapp` | — | P2.1, P2.3, P2.4, P2.5 |
| | P2.3 | Integridade do app `finances` (guards de escrita, fechamento) | `fix/finances-integrity-guards` | — | P2.1, P2.2, P2.4, P2.5 |
| | P2.4 | Integridade de dados do core (constraints, soft-delete, CPF) | `fix/core-data-integrity` | — | P2.1, P2.2, P2.3, P2.5 |
| | P2.5 | Fronteira de timezone SP + bugs de dinheiro no legado + fix dado | `fix/timezone-and-legacy-money` | — | P2.1, P2.2, P2.3, P2.4 |
| **P3 — Mobile** | P3.1 | Mobile: auth (token no body) + correção dos contratos de API | `fix/mobile-api-realignment` | P1.2 (ideal) | — |
| | P3.2 | Mobile: quality gates + Zod runtime + remoção do financeiro legado | `chore/mobile-quality-gates` | P3.1 | — |
| **P4 — Arquitetura** | P4.1 | Camadas do backend: extrair services, padronizar erros, validar input | `refactor/backend-layering` | P2.* (✓) | P4.2 |
| | P4.2 | Resiliência de cache + reescrita da invalidação do core | `fix/cache-resilience` | — | P4.1, P4.3 |
| | P4.3 | Frontend: dedup de modais + criação atômica + gotcha Zod + dead code | `refactor/frontend-quality` | **P4.1** (atômico+`LeaseCreationService`) | P4.2 |
| **P5 — Performance** | P5.1 | Backend: N+1, IBGE assíncrono, memoização | `perf/backend-queries` | P4.1 (ideal) | P5.2 |
| | P5.2 | Frontend: lazy `xlsx` + filtro de competência nas Contas | `perf/frontend-bundle` | — | P5.1 |
| **P6 — Testes/Docs/CI** | P6.1 | Qualidade de testes: warnings, mock policy, factories, gaps | `test/quality-hardening` | P2–P5 (ideal) | P6.2, P6.3 |
| | P6.2 | Sincronização de documentação com a realidade | `docs/sync-with-reality` | P2–P5 (ideal) | P6.1, P6.3 |
| | P6.3 | CI, gates e higiene de build/deploy | `chore/ci-and-build-hygiene` | P0.1 | P6.1, P6.2 |
| **P7 — Legado** | P7.1 | Remoção do módulo financeiro pessoal legado (BE+FE+mobile) | `refactor/remove-legacy-financial` | `finances/` cobrir tudo + P3.2 | — |
| **P8 — Features** | P8.1 | Roadmap de features (ondas) — gates de brainstorming | por feature | P0–P2 | — |

---

## Resumo por fase

### P0 — Incidente de segurança (fazer **primeiro**, isolado)
Vazamento de dados pessoais (LGPD) e hashes de senha de admins commitados no git, hooks de proteção inertes, `.gitignore` com buracos, e arquivos mortos perigosos (`generate_notice_pdf.py`, `database_migration_scripts.sql`, stack Docker quebrada). **Bloqueia confiança em tudo o mais** — purgar histórico + rotacionar segredos antes de seguir.

### P1 — Hardening de segurança crítico
Quatro furos exploráveis: arquivos sensíveis servidos sem auth (contratos com CPF enumeráveis), inquilino autenticado lê todos os dados financeiros/PII, SSTI/RCE + path traversal no editor de template, e validações de upload/OTP/OAuth/senha fracas.

### P2 — Correção de dinheiro e dados
Bugs que calculam dinheiro errado ou corrompem dados: `late_fee` cego a mês/ano, soft-deleted vazando para o PDF do contrato, PIX que quebra com acentos, guards de integridade ausentes no `finances` (fechamento/parcelamento), constraints/normalização ausentes no core, e fronteira de timezone. Inclui o fix do dado vivo do apto 203/850.

### P3 — Realinhamento do mobile
O app Expo está quebrado contra o backend (auth por cookie, dual pattern, shapes divergentes, paginação). Corrigir auth + contratos, adicionar quality gates, e remover as telas do financeiro legado.

### P4 — Arquitetura e qualidade
Mover lógica de negócio para services, padronizar erros, resiliência de cache + reescrita da invalidação morta, unificação dos modais de lease + criação atômica, e o gotcha Zod do dual pattern.

> **STATUS (2026-06-12, branch `refactor/p4-architecture-quality`):** P4.1 **EXECUTADO** (47e85d1) · P4.2 **EXECUTADO** (34dfe98) · P4.3 **EXECUTADO PARCIAL** (90aef43 — bugs ativos: condominium_id, expense read schema, global-search, finance cache, aria-labels). Deferidos p/ PR focado: endpoint atômico + unificação LeaseFormModal, parseList sweep, client.ts unwrap, main-layout useCurrentUser, /admin/users sidebar, datas legadas. `{"error"}`→`{"detail"}` sweep deferido p/ P6. Full backend suite 2482 passed; frontend 926 tests + lint + type-check verdes.

### P5 — Performance
N+1 nos serializers e dashboards, chamada síncrona ao IBGE no request, memoização de recomputações, e bundle do frontend (`xlsx` lazy + filtro de competência).

### P6 — Testes, docs, CI e higiene
Remover supressões de warning, migrar testes para a fronteira HTTP (mock policy), corrigir flakiness das factories, sincronizar toda a documentação com a realidade, e alinhar o CI ao gate canônico (incluir `finances/` e pyright).

### P7 — Remoção do legado
Desacoplar os 2 pontos `use-persons` (refactor explicit-owner), depois deletar em bloco ~18k LOC do frontend legado + models/services/viewsets do backend legado. **Só após o `finances/` cobrir 100% e com backup.**

### P8 — Features novas (nível de mercado jun/2026)
Quatro ondas priorizadas. Onda 1 (maior ROI): conciliação PIX automática, cockpit fiscal Carnê-Leão/IRPF, régua de cobrança, assinatura eletrônica. Cada feature passa por `/brainstorming` → design doc → prompts TDD antes de codar.

---

## Gate global de "pronto para produção" (após P0–P6)

- [ ] Nenhum dump/PII/segredo no histórico git; hooks instalados e funcionando
- [ ] Nenhum arquivo sensível servido sem autenticação; inquilino não acessa dados administrativos/financeiros
- [ ] `SandboxedEnvironment` no template; sem path traversal
- [ ] `late_fee` correto cross-month; soft-deleted não vazam; PIX e WhatsApp funcionam
- [ ] Guards de integridade no `finances`; constraints e normalização no core
- [ ] Mobile: login/refresh/PIX/criar-locação funcionam; quality gates ativos
- [ ] Cache degrada graciosamente se Redis cair; invalidação real
- [ ] CI roda ruff+mypy+pyright+pytest sobre `core/`+`finances/`+`tests/` e os gates do frontend
- [ ] Documentação reflete `finances/`+`mobile/` e as rotas reais
- [ ] Coverage ≥ 90% mantido
