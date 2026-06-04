# Sessão 32 — Backend: envio dual-channel (Expo+WebPush) + WebPushViewSet + rotas

> Parte da feature "App Mobile Completo — PWA + Offline + Web Push" (Frente D). Esta sessão é **só
> backend**: refatora `notification_service.py` para enviar por **dois canais** (Expo já existente +
> Web Push novo) e adiciona o `WebPushViewSet` (`subscribe`/`unsubscribe`/`vapid-public-key`) +
> rotas. **Depende da Sessão 31** (model `WebPushSubscription` + settings VAPID + dep `pywebpush`
> já no `requirements.txt`/`pyproject.toml`). Não mexe no model (S31) nem nos gatilhos.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro, foco na **Frente D §7.2 / §7.3**, §9 deps/env): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (confirmar **Sessão 31 concluída** antes de começar: model `WebPushSubscription` migrado, settings `VAPID_*` presentes, `pywebpush` em `requirements.txt` **e** `pyproject.toml`)
- Regras do projeto: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — abrir e seguir)
- **Service de notificação inteiro (refatorar)**: `core/services/notification_service.py:1-127`. Em especial:
  - `create_notification` `:22-44` — **inalterado** (assinatura/comportamento; segue chamando `send_push_notification`).
  - `send_push_notification` `:47-79` — extrair a lógica Expo (`:60-79`) para `send_expo_push` e passar a chamar **os dois** canais.
  - Padrão de logging silencioso `:78-79` (`logger.warning(...)`, falha não propaga — a `Notification` já está persistida).
  - Gatilhos a **NÃO** tocar: `notify_new_proof` `:90-102`, `notify_proof_reviewed` `:105-126`.
- **ViewSet a espelhar (estilo/idioma/validação/HTTP codes)**: `core/viewsets/device_views.py:23-94` (`DeviceTokenViewSet`):
  - `permission_classes = [IsAuthenticated]` `:26`; `@action(detail=False, methods=["post"], url_path="register")` `:28`.
  - `update_or_create(..., defaults=..., create_defaults=...)` `:51-66` + `cast(User, request.user)` `:50`.
  - retorno `201/200` `:67-70`; validação `400` `:39-48`; `unregister` → `update(is_active=False)` + `404` `:72-94`.
- **Registro de export do ViewSet**: `core/viewsets/__init__.py:12,39-62` (import + `__all__` ordenado alfabeticamente).
- **Registro de rota no router**: `core/urls.py:15-38` (import do `.viewsets`), `:79` (`router.register(r"devices", DeviceTokenViewSet, basename="devices")`).
- **Teste de service (unit, mock só do boundary HTTP)**: `tests/unit/test_notification_service.py:1-157` — fixtures, `patch("core.services.notification_service.http_requests.post")` `:84,114,122`, asserções de chamada `:117-119` / `assert_not_called` `:125`.
- **Teste de API do ViewSet (integration, a espelhar)**: `tests/integration/test_device_api.py:1-97` — `authenticated_api_client`/`api_client` (conftest), `register`→201, duplicado→200, `unregister`→200 + `is_active=False`, campos faltando→400, inexistente→404, sem auth→401.
- **Fixtures de auth (conftest)**: `tests/conftest.py:53` (`api_client`, não autenticado), `:66` (`admin_user`), `:96` (`authenticated_api_client` = admin autenticado).

### Contrato cross-session (NÃO redefinir — usar verbatim)
- **Model `WebPushSubscription` (criado na S31)** — campos: `user` (FK, related_name `web_push_subscriptions`), `endpoint` (TextField **unique**), `p256dh` (CharField), `auth` (CharField), `is_active` (bool, default True). Sem SoftDelete (espelha `DeviceToken`). Importar de `core.models`.
- **Settings VAPID (criados na S31)**: `settings.VAPID_PUBLIC_KEY`, `settings.VAPID_PRIVATE_KEY`, `settings.VAPID_SUBJECT`.
- **Shape do payload `subscribe` (idêntico ao que a S33 envia via `subscription.toJSON()`)**:
  `{ "endpoint": str, "keys": { "p256dh": str, "auth": str } }`.
- **Resposta de `vapid-public-key`**: `{ "publicKey": settings.VAPID_PUBLIC_KEY }`.
- **Rotas finais**: `GET /api/web-push/vapid-public-key/`, `POST /api/web-push/subscribe/`, `POST /api/web-push/unsubscribe/` (basename `web-push`).

## Escopo

### Arquivos a criar
- `core/viewsets/web_push_views.py` — `WebPushViewSet(ViewSet)`.
- `tests/integration/test_web_push_api.py` — testes de API (subscribe/unsubscribe/vapid-public-key).
- `tests/unit/test_web_push_sender.py` — testes unit de `send_web_push` + `send_push_notification` dual-channel.

### Arquivos a modificar
- `core/services/notification_service.py` — extrair `send_expo_push`; criar `send_web_push`; `send_push_notification` chama os dois.
- `core/viewsets/__init__.py` — import + `__all__` para `WebPushViewSet`.
- `core/urls.py` — import + `router.register(r"web-push", WebPushViewSet, basename="web-push")`.

## Especificação

### `core/services/notification_service.py`
Manter `create_notification` e os gatilhos **inalterados**. Imports novos no topo do arquivo (sem `try/except ImportError`, sem `if TYPE_CHECKING`, sem `from __future__`):

```python
from django.conf import settings
from pywebpush import WebPushException, webpush
from core.models import DeviceToken, Notification, PaymentProof, WebPushSubscription
```

1. **`send_expo_push(user: User, title: str, body: str, data: dict | None = None) -> None`**
   - Mover, **sem alterar comportamento**, o corpo atual de `send_push_notification` `:60-79` (query `DeviceToken.objects.filter(user=user, is_active=True)`, early-return sem devices, montagem de `messages`, `http_requests.post(...)` com `try/except http_requests.RequestException` → `logger.warning(...)`).

2. **`send_web_push(user: User, title: str, body: str, data: dict | None = None) -> None`**
   - Iterar `WebPushSubscription.objects.filter(user=user, is_active=True)`.
   - Para cada inscrição, montar `subscription_info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}` e o payload JSON `json.dumps({"title": title, "body": body, "data": data or {}})`.
   - Chamar `webpush(subscription_info=..., data=payload, vapid_private_key=settings.VAPID_PRIVATE_KEY, vapid_claims={"sub": settings.VAPID_SUBJECT})`.
   - `except WebPushException as exc:` — se `exc.response is not None and exc.response.status_code in (404, 410)`: desativar a inscrição (`sub.is_active = False; sub.save(update_fields=["is_active"])`). Em qualquer `WebPushException`, **logar e seguir** (`logger.warning("Failed web push to user %s: %s", user.pk, exc)`) — nunca propagar (a `Notification` já está persistida).
   - Constantes: extrair `_GONE_STATUS_CODES = (404, 410)` no topo do módulo (sem magic numbers).

3. **`send_push_notification(user, title, body, data=None) -> None`** (mesma assinatura)
   - Corpo passa a ser: `send_expo_push(user, title, body, data)` **e** `send_web_push(user, title, body, data)`. Sem outra lógica.

> `import json` no topo (não está hoje). Tipar tudo (mypy strict). Sem docstrings supérfluas — só onde a lógica não é óbvia (padrão do arquivo atual).

### `core/viewsets/web_push_views.py`
Espelhar `DeviceTokenViewSet` exatamente em estilo/idioma/HTTP codes:

```python
class WebPushViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="vapid-public-key")
    def vapid_public_key(self, request: Request) -> Response: ...

    @action(detail=False, methods=["post"], url_path="subscribe")
    def subscribe(self, request: Request) -> Response: ...

    @action(detail=False, methods=["post"], url_path="unsubscribe")
    def unsubscribe(self, request: Request) -> Response: ...
```

- **`vapid_public_key`** (GET): retorna `Response({"publicKey": settings.VAPID_PUBLIC_KEY})` (200). Sem validação de body.
- **`subscribe`** (POST): ler `endpoint = request.data.get("endpoint", "").strip()` e `keys = request.data.get("keys") or {}`; `p256dh = keys.get("p256dh", "").strip()`, `auth = keys.get("auth", "").strip()`. Se faltar `endpoint`, `p256dh` ou `auth` → `400` `{"error": "endpoint e keys (p256dh, auth) são obrigatórios"}`. Caso ok: `authenticated_user = cast(User, request.user)` e `WebPushSubscription.objects.update_or_create(endpoint=endpoint, defaults={...}, create_defaults={...})` espelhando `DeviceTokenViewSet:51-66` (em `defaults`: `user`, `p256dh`, `auth`, `is_active=True`, `updated_by`; em `create_defaults`: o mesmo + `created_by`). Retornar `{"id": sub.pk, "endpoint": sub.endpoint}` com `201_CREATED` se `created` senão `200_OK`.
- **`unsubscribe`** (POST): `endpoint = request.data.get("endpoint", "").strip()`; vazio → `400` `{"error": "endpoint é obrigatório"}`. `updated = WebPushSubscription.objects.filter(endpoint=endpoint, user=cast(User, request.user)).update(is_active=False)`; `updated == 0` → `404` `{"error": "Inscrição não encontrada"}`; senão `Response({"message": "Inscrição removida"})` (200).
- Imports: `from django.conf import settings`, `from typing import cast`, `from django.contrib.auth.models import User`, DRF `status/action/IsAuthenticated/Request/Response/ViewSet`, `from core.models import WebPushSubscription`.

### `core/viewsets/__init__.py` e `core/urls.py`
- `__init__.py`: `from .web_push_views import WebPushViewSet` + adicionar `"WebPushViewSet"` no `__all__` (ordem alfabética — após `RentPaymentViewSet`).
- `urls.py`: adicionar `WebPushViewSet` ao bloco de import `from .viewsets import (...)` e registrar `router.register(r"web-push", WebPushViewSet, basename="web-push")` junto aos demais registros (próximo a `devices`).

## TDD

Rodar **somente os arquivos de teste desta sessão** (a suíte completa tem problemas pré-existentes de xdist/Redis — ver memória do projeto). **Mockar APENAS o boundary externo**: `pywebpush.webpush` e `http_requests.post` (HTTP). **NUNCA** mockar ORM, o model, os services internos (`send_expo_push`/`send_web_push` são exercitados de verdade; em `send_push_notification` faz-se patch nas duas funções de canal **porque são os boundaries de envio**, conforme `test_notification_service.py:84`).

### 1. Red — escrever os testes primeiro (devem falhar: símbolos/rotas inexistentes)
Comando: `python -m pytest tests/integration/test_web_push_api.py tests/unit/test_web_push_sender.py -v`

**`tests/integration/test_web_push_api.py`** (espelhar `test_device_api.py`; URLs: `/api/web-push/...`):
- `test_vapid_public_key_returns_key` — GET autenticado → 200 e `response.data["publicKey"] == settings.VAPID_PUBLIC_KEY` (usar `override_settings(VAPID_PUBLIC_KEY="test-pub-key")`).
- `test_subscribe_creates_subscription` — POST `{ "endpoint": "...", "keys": {"p256dh": "...", "auth": "..."} }` → 201; `response.data["endpoint"]` confere; `WebPushSubscription.objects.filter(endpoint=..., user=admin_user, is_active=True).exists()`.
- `test_subscribe_same_endpoint_updates_existing` — dois POSTs com o mesmo `endpoint` (segundo com `p256dh/auth` diferentes) → 2º responde 200 e `WebPushSubscription.objects.filter(endpoint=...).count() == 1` (chaves atualizadas).
- `test_subscribe_missing_keys_returns_400` — body sem `keys` (ou `keys` sem `p256dh`/`auth`) → 400.
- `test_subscribe_missing_endpoint_returns_400` — body sem `endpoint` → 400.
- `test_unsubscribe_deactivates_subscription` — cria via subscribe, depois POST `unsubscribe {endpoint}` → 200 e `WebPushSubscription.objects.filter(endpoint=..., is_active=False).exists()`.
- `test_unsubscribe_nonexistent_returns_404` — `unsubscribe` de endpoint inexistente → 404.
- `test_unsubscribe_missing_endpoint_returns_400` — body vazio → 400.
- `test_subscribe_requires_authentication` — `api_client` (sem auth) → 401.

**`tests/unit/test_web_push_sender.py`** (mock só do boundary `pywebpush`):
- `test_send_web_push_calls_webpush_for_active_subscription` — cria `WebPushSubscription(is_active=True)`; `patch("core.services.notification_service.webpush")` → `send_web_push(...)` chama `webpush` 1×; `subscription_info`/`data`/`vapid_private_key`/`vapid_claims` corretos (asserir `call_args.kwargs`).
- `test_send_web_push_skips_inactive_subscription` — inscrição `is_active=False` → `webpush` não chamado.
- `test_send_web_push_deactivates_on_410` — `webpush` levanta `WebPushException` com `response.status_code == 410` (construir um objeto de resposta simples como boundary: ex. `WebPushException("gone", response=SimpleNamespace(status_code=410))`); após `send_web_push`, a inscrição fica `is_active=False` (refetch do DB). **Não** propaga exceção.
- `test_send_web_push_keeps_subscription_on_other_error` — `WebPushException` com `response.status_code == 500` (ou `response=None`) → inscrição permanece `is_active=True`; sem exceção propagada.
- `test_send_push_notification_calls_both_channels` — `patch("core.services.notification_service.send_expo_push")` **e** `patch("core.services.notification_service.send_web_push")`; `send_push_notification(user, "T", "B", {"k": "v"})` → ambos chamados 1× com `(user, "T", "B", {"k": "v"})`.

> Fixture local mínima de usuário: reusar `admin_user` do conftest. Para `WebPushSubscription`, criar via `WebPushSubscription.objects.create(user=admin_user, endpoint=..., p256dh=..., auth=..., is_active=..., created_by=admin_user, updated_by=admin_user)` (model real, sem mock).

### 2. Green — implementar o mínimo para os testes passarem
Refatorar `notification_service.py` (extrair `send_expo_push`, criar `send_web_push`, religar `send_push_notification`), criar `web_push_views.py`, registrar em `__init__.py` + `urls.py`.

### 3. Refactor — `_GONE_STATUS_CODES` constante; helper de leitura do payload no viewset se reduzir duplicação; sem comentários supérfluos; funções pequenas e de responsabilidade única.

### 4. Verify
- `python -m pytest tests/integration/test_web_push_api.py tests/unit/test_web_push_sender.py -v` → tudo verde.
- `ruff check && ruff format --check` → zero erros/avisos.
- `mypy core/` → zero erros nos arquivos tocados.
- `pyright` → zero erros nos arquivos tocados.

## Constraints (NÃO fazer)

- **NÃO** alterar `create_notification` (assinatura/comportamento) nem os gatilhos `notify_new_proof`/`notify_proof_reviewed`/`send_scheduled_notifications` — eles passam a enviar Web Push **automaticamente** via `send_push_notification`, sem edição.
- **NÃO** mexer no model `WebPushSubscription` nem na migração (Sessão 31) — só consumir.
- **NÃO** adicionar/alterar settings `VAPID_*` aqui (Sessão 31). **NÃO** reinstalar `pywebpush` nem reescrever `requirements.txt`/`pyproject.toml` — já feito na S31; apenas **importar** `pywebpush` diretamente no topo (sem `try/except ImportError`, sem `HAS_*` flag).
- **NÃO** mockar internals: ORM, model, `send_expo_push`/`send_web_push` (estes são exercitados de verdade em seus próprios testes). O **único** patch permitido é o boundary externo: `pywebpush.webpush` e `http_requests.post`. No teste de `send_push_notification`, patchar as duas funções de canal é aceito **porque elas são a fronteira de envio** (mesmo padrão de `test_notification_service.py`).
- **NÃO** usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore` — corrigir o código na raiz.
- **NÃO** usar `from __future__ import annotations` (PEP 649 nativo no 3.14); **NÃO** usar `if TYPE_CHECKING:` — importar tipos diretamente.
- **NÃO** criar re-exports/barrels além do `__all__` já existente; consumidores importam da fonte.
- **NÃO** rodar a suíte completa (apenas os 2 arquivos desta sessão) — evitar falhas pré-existentes de xdist/Redis.
- SOLID/DRY/KISS/YAGNI — sem código especulativo (ex.: não adicionar endpoint de "listar inscrições" não pedido).

## Critérios de Aceite

- [ ] `notification_service.py` expõe `send_expo_push`, `send_web_push` e `send_push_notification` (esta chamando os dois canais); `create_notification` e os gatilhos **inalterados**.
- [ ] `send_web_push` itera `WebPushSubscription.objects.filter(user, is_active=True)`, chama `webpush(...)` com VAPID dos `settings`, e desativa a inscrição (`is_active=False`) quando `WebPushException` traz status `404`/`410`; outras falhas logadas e silenciosas.
- [ ] `WebPushViewSet(ViewSet)` com `permission_classes=[IsAuthenticated]` e as 3 actions (`vapid-public-key` GET, `subscribe` POST, `unsubscribe` POST) espelhando `DeviceTokenViewSet` (400/201/200/404).
- [ ] `subscribe` faz `update_or_create` por `endpoint`; payload lido como `{ endpoint, keys: { p256dh, auth } }`.
- [ ] `WebPushViewSet` exportado em `core/viewsets/__init__.py` (`__all__`) e rota registrada em `core/urls.py` com basename `web-push` → `/api/web-push/{vapid-public-key,subscribe,unsubscribe}/`.
- [ ] `tests/integration/test_web_push_api.py` e `tests/unit/test_web_push_sender.py` cobrem todos os cenários listados e estão 100% verdes.
- [ ] Mock apenas do boundary externo (`webpush`/`http_requests.post`); sem mock de ORM/model/services internos.
- [ ] `ruff check && ruff format --check`, `mypy core/`, `pyright` sem erros/avisos nos arquivos tocados.
- [ ] Sem `# noqa`/`# type: ignore`; sem `from __future__`/`TYPE_CHECKING`; sem re-export/barrel novo; `pywebpush` importado direto (sem `try/except ImportError`).
- [ ] Nenhuma alteração em `requirements.txt`/`pyproject.toml`/`settings.py`/migrações/model (escopo da S31).

## Handoff

1. Rodar e confirmar verde (colar saída como evidência):
   - `python -m pytest tests/integration/test_web_push_api.py tests/unit/test_web_push_sender.py -v`
   - `ruff check && ruff format --check`
   - `mypy core/`
   - `pyright`
2. Atualizar `prompts/SESSION_STATE.md`: marcar **Sessão 32 concluída**; anotar arquivos criados (`web_push_views.py`, `test_web_push_api.py`, `test_web_push_sender.py`) e modificados (`notification_service.py`, `viewsets/__init__.py`, `urls.py`); registrar que o **envio dual-channel está ativo** (todos os gatilhos já enviam Web Push) e que a **Sessão 33** (frontend: handlers `push`/`notificationclick` em `app/sw.ts`, hook `use-web-push.ts`, toggle `push-toggle.tsx`) consome `/api/web-push/*` com o shape `{ endpoint, keys: { p256dh, auth } }`.
3. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(backend): dual-channel push (expo+webpush) and web-push subscribe endpoints

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
4. A Sessão 33 começa lendo o `SESSION_STATE.md`.
