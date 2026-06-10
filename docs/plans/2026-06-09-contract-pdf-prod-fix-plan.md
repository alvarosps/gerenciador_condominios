# Fix: Geração de Contrato PDF falha em PROD (Proxy Error / fetch failed)

**Data:** 2026-06-09 · **Sintoma:** `POST /api/leases/65/generate_contract/` → 500 `{error: "Proxy Error", details: "fetch failed"}` no Vercel.

## Root Cause

Cadeia causal (todas as camadas verificadas no código):

1. **Sem broker Celery em PROD** → `condominios_manager/settings.py:520-522`: `CELERY_TASK_ALWAYS_EAGER = not CELERY_BROKER_URL`. No Render não há `CELERY_BROKER_URL`, então `generate_contract_pdf.delay()` (`core/views.py:376`) executa **sincronamente dentro do worker web do gunicorn**.
2. A task lança **Chromium headless via Playwright dentro do request** (`core/infrastructure/pdf_generator.py:87-95`), no instance do Render (free tier: 512 MB RAM / 0.1 CPU; runtime nativo — `render_build.sh` instala o Chromium com `PLAYWRIGHT_BROWSERS_PATH=0`; o Dockerfile **não** é usado pelo Render e seu comentário já avisa: *"PDF generation must run in a dedicated Celery worker container"*).
3. O processo worker do gunicorn **morre no meio do request** (sem resposta HTTP) → conexão TCP resetada.
4. O proxy do Vercel (`frontend/app/api/[...route]/route.ts:33-60`) tem o `fetch` rejeitado com `fetch failed` → catch-all devolve 500 `{error: "Proxy Error"}`.

**Por que sabemos que o worker morreu (e não foi um 500 do Django):** um erro Python (ex.: Chromium ausente) seria capturado pelo viewset (`core/views.py:377-405`) e devolvido como 500/400 **com corpo JSON do Django**, que o proxy repassaria. `fetch failed` só acontece com falha de conexão. Os GETs imediatamente anteriores funcionaram (backend de pé), e o axios tem timeout de 30s (`frontend/lib/api/client.ts:5`) — o cliente recebeu o 500 do proxy **antes** do timeout, então a morte ocorreu em <30s.

**Assassino mais provável: OOM** (Django + driver Node do Playwright + Chromium ≈ 450-600 MB > 512 MB; falha rápida <30s é consistente). Hipótese secundária: timeout do worker do gunicorn (default 30s se o start command não define `--timeout`). Fatores agravantes: launch args sem `--disable-dev-shm-usage`/`--disable-gpu` (crash clássico de Chromium em container com `/dev/shm` pequeno).

Bug "nunca funcionou em prod" (ambiental/arquitetural), não regressão — deploy é de 2026-06-05.

## Fase 0 — Confirmar diagnóstico (Render/Vercel dashboards, ~10 min)

- [ ] Logs do Render em 2026-06-09 ~22:58 UTC: procurar `Out of memory` / `Killed` / restart de instância (→ OOM) **ou** `[CRITICAL] WORKER TIMEOUT` (→ timeout).
- [ ] Anotar: plano/RAM da instância, **start command atual** (nº de workers, `--timeout`), env vars presentes (`REDIS_URL`, `CELERY_BROKER_URL`).
- [ ] Vercel: confirmar Fluid Compute ativo (teto de `maxDuration` no Hobby = 300s).
- [ ] Verificar se há timeout de request no edge do Render (doc oficial) — limita o teto do caminho síncrono.

## Fase 1 — Hardening de código (vale para qualquer variante)

1. [x] **Flags do Chromium** em `core/infrastructure/pdf_generator.py`: `--disable-dev-shm-usage` e `--disable-gpu` adicionados (TDD: `test_generate_pdf_launches_with_container_hardening_flags`).
2. [x] **Proxy honesto**: falha de fetch upstream → **502** `{error: 'Bad Gateway', details}` (TDD: `app/api/[...route]/__tests__/route.test.ts`).
3. [x] Gate: ruff + format + mypy + pyright + pytest (37/37 infra) | ESLint + tsc + vitest (22/22) — tudo limpo (2026-06-09).

## Fase 2 — Fix recomendado nº 1: caminho síncrono dimensionado (custo R$ 0)

A ação é rara (poucos contratos/mês) e o footprint síncrono é o MENOR possível (sem processo extra) — KISS para o free tier:

- [ ] **Start command no Render** (DASHBOARD — único item manual restante): `gunicorn condominios_manager.wsgi:application --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --bind 0.0.0.0:$PORT`
  - 1 processo (~160 MB) + threads para concorrência → sobra de RAM para o burst do Chromium (~250-300 MB).
  - Playwright sync API funciona em thread gthread (sem event loop asyncio na thread).
- [x] **Timeout do axios por request**: `useGenerateContract` com `timeout: 180_000`.
- [x] **`export const maxDuration = 180`** no proxy route — requer Fluid Compute (verificar na Fase 0; sem Fluid no Hobby o teto é 60 e o deploy pode falhar → reduzir para 60).
- [x] UX: texto do modal ajustado para "pode levar até 1 minuto".
- Limitação conhecida: 2 gerações simultâneas = 2 Chromiums (OOM). Aceitável (single admin); não construir lock (YAGNI).

## Fase 3 — Escalação (se Fase 4 mostrar OOM persistente ou UX inaceitável): completar a arquitetura assíncrona

O backend já tem o caminho pronto (`tasks.py`, branch 202 em `views.py:385-389`, endpoint `api/tasks/<task_id>/status/` em `urls.py:54`); falta broker, worker e frontend:

- [ ] **Infra**: Render Key Value (free 25 MB, `maxmemory-policy noeviction`) → `CELERY_BROKER_URL` e `CELERY_RESULT_BACKEND` no Render.
- [ ] **Settings**: adicionar `CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)`, `CELERY_TASK_TIME_LIMIT = 180`, `CELERY_RESULT_EXPIRES = 3600`.
- [ ] **Worker dedicado**: Background Worker no Render (Starter ~US$ 7/mês, 512 MB isolados) com mesmo build (`render_build.sh` já instala Chromium) e start `celery -A condominios_manager worker --pool=solo --concurrency=1`.
  - Variante R$ 0 (web+worker na mesma instância via script de start) **piora** a memória (+~150 MB) — só faz sentido se Fase 0 provou timeout, não OOM.
- [ ] **Frontend**: `useGenerateContract` passa a tratar **200 (eager — dev local continua sem broker)** e **202 + polling** em `/tasks/{task_id}/status/` (intervalo 2,5s, cap 3 min); Zod schema para união das respostas; estados do modal (gerando → sucesso/falha); testes Vitest+MSW: sucesso eager, sucesso após N polls, falha de task, timeout de polling.
- [ ] Bonus: apontar `REDIS_URL` para o mesmo Key Value → cache real em prod (invalidação por signals passa a valer).

## Fase 4 — Validação em PROD (gate final)

- [ ] Deploy; gerar contrato real (lease 65) logado como admin.
- [ ] Acompanhar **Memory graph + Events** do Render durante a geração (sem OOM/restart, sem `WORKER TIMEOUT` nos logs).
- [ ] Baixar o PDF via botão (rota `/download`) e conferir conteúdo/layout.
- [ ] Confirmar `NEXT_PUBLIC_BACKEND_URL` setado no Vercel (visualização/anexos — fix antigo já aplicado em `contract-view-modal.tsx:30`).

## Notas / Riscos

- **Storage efêmero no Render**: `FileSystemDocumentStorage` grava em disco local — PDFs somem a cada deploy/restart. Mitigação atual: regenerar. Futuro (fora de escopo): Supabase Storage atrás de `IDocumentStorage`.
- **Última alternativa** se Chromium não couber em 512 MB e não quiser pagar worker: trocar engine para WeasyPrint (sem Chromium/Node). Mudança maior — exige validação visual rigorosa do contrato (documento legal) e confirmação das libs de sistema (pango/cairo) no runtime nativo do Render.
- Não tocar no fluxo dev local: continua eager (sem broker), por isso o hook deve sempre suportar resposta 200 direta.
