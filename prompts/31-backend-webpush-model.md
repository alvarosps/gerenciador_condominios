# Sessão 31 — Backend: model `WebPushSubscription` + migração + config VAPID + dep `pywebpush`

> Parte da feature "App Mobile Completo (Responsividade + PWA + Offline + Web Push)" — **Frente D**.
> Esta sessão entrega **somente a fundação de dados/config do Web Push**: o model, a migração, as três
> settings VAPID (via `python-decouple`), a documentação de env e a dependência `pywebpush`. O **envio**
> (`notification_service`) e os **endpoints** (`WebPushViewSet`/rotas) são a **Sessão 32** — não tocar aqui.

## Contexto

Ler antes de tocar em qualquer arquivo:
- Design doc (ler inteiro; foco em §7.1 "Backend — model e migração", §7.3 config/dep, §3 decisão "Novo model `WebPushSubscription`", §9 dependências/env): `@docs/plans/2026-06-04-mobile-pwa-offline-design.md`
- Padrão de prompts (estrutura/exemplares): `@prompts/00-prompt-standard.md`
- Estado das sessões: `@prompts/SESSION_STATE.md` (a feature Web Push começa nesta Sessão 31)
- Regras do projeto: `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/coding-standards.md`, `.claude/rules/design-principles.md`, `.claude/rules/database.md`, `.claude/rules/security.md`, `tests/CLAUDE.md`

### Exemplares (arquivo:linha — exemplar > descrição, abrir e seguir)
- **Model de push sem SoftDelete a espelhar (forma EXATA: `AuditMixin` only, FK `user` com `related_name`, campo `unique`, `is_active` default True, `__str__`)**: `core/models.py:1565-1583` (`DeviceToken(AuditMixin, models.Model)`). O novo model é o análogo Web Push: mesma estrutura, campos diferentes.
- **`AuditMixin` (o único mixin a herdar; provê created/updated_at/by; `save()` atualiza `updated_at`)**: `core/models.py:61-108`.
- **Padrão `config(...)` do `python-decouple` (string com default, sem cast)**: `condominios_manager/settings.py:499-504` (bloco Twilio — strings com `default=""`). Bloco onde adicionar as settings VAPID: **após** o bloco Twilio, **antes** de "Celery Configuration" (`settings.py:504-506`).
- **`requirements.txt` — bloco "WhatsApp / SMS" como vizinho de estilo**: `requirements.txt:54-55` (`twilio>=9.0.0,<10.0`). Adicionar `pywebpush` num bloco próprio comentado.
- **`pyproject.toml` `[project.dependencies]` — entrada espelhada de `requirements.txt`**: `pyproject.toml:56-57` (`"twilio>=9.0.0,<10.0",`). A mesma dep entra nos **dois** arquivos (regra do projeto).
- **Doc de env (estilo de seção comentada)**: `.env.example:142-156` (seção "APPLICATION SETTINGS") e `.env.production.example:98-105` (seção "APPLICATION CONSTANTS"). Adicionar uma nova seção "WEB PUSH (VAPID)" em ambos.
- **Teste de model (`__str__`, criação, herança de mixin)**: `tests/unit/test_models.py:1-26` (imports + estilo) e fixtures `:33-55`. Fixture de usuário pronta no `conftest.py`: `regular_user` (`tests/conftest.py:80-92`) — usar para o teste de `related_name`/FK.

### Contrato compartilhado (nomes EXATOS — usados verbatim na Sessão 32)
A Sessão 32 (viewset + sender) lê estes campos pelo nome; **não** renomear nem reordenar a semântica:
- Model `WebPushSubscription(AuditMixin)` com campos: `user` (FK → `settings.AUTH_USER_MODEL`, `related_name="web_push_subscriptions"`), `endpoint` (`TextField(unique=True)`), `p256dh` (`CharField(max_length=255)`), `auth` (`CharField(max_length=255)`), `is_active` (`BooleanField(default=True)`).
- Sem `SoftDeleteMixin` (espelha `DeviceToken`/`Notification`).
- Settings: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (default `mailto:admin@example.com`).
- Dep: `pywebpush`.

## Escopo

### Arquivos a criar
- `tests/unit/test_web_push_model.py` — testes do model `WebPushSubscription`.
- `core/migrations/0044_webpushsubscription.py` — **gerado** por `makemigrations` (nome final pode variar; head atual é `0043_alter_lease_tag_deposit_paid_alter_lease_tag_fee` → próximo é `0044`). **Não escrever à mão.**

### Arquivos a modificar
- `core/models.py` — adicionar a classe `WebPushSubscription` (logo após `DeviceToken`, antes de `PaymentProof`).
- `condominios_manager/settings.py` — adicionar bloco "Web Push (VAPID)" com as 3 settings via `config(...)`.
- `requirements.txt` — adicionar `pywebpush`.
- `pyproject.toml` — adicionar `pywebpush` em `[project.dependencies]`.
- `.env.example` — documentar `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT`.
- `.env.production.example` — idem.

## Especificação

### Model `core/models.py` (espelhar `DeviceToken` em `:1565-1583`)
```python
class WebPushSubscription(AuditMixin, models.Model):
    """Web Push (VAPID) subscriptions for browser push notifications."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="web_push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Web push for {self.user}"
```
- `settings` e `models` já estão importados no topo de `core/models.py` — **não** reimportar.
- **NÃO** herdar `SoftDeleteMixin` (igual `DeviceToken`). Sem `Meta.indexes` (o `unique=True` no `endpoint` já cria índice; YAGNI).
- **NÃO** usar `URLField` no `endpoint`: endpoints de push frequentemente excedem 200 chars e não precisam de validação de URL — `TextField(unique=True)` conforme contrato.

### Settings `condominios_manager/settings.py` (após o bloco Twilio `:499-504`)
```python
# Web Push (VAPID) settings
VAPID_PUBLIC_KEY = config("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = config("VAPID_PRIVATE_KEY", default="")
VAPID_SUBJECT = config("VAPID_SUBJECT", default="mailto:admin@example.com")
```

### Dependência `pywebpush` (nos DOIS arquivos — regra do projeto)
- `requirements.txt`: adicionar um bloco próprio (estilo `requirements.txt:54-55`):
  ```
  # Web Push (VAPID)
  pywebpush>=2.0.0,<3.0
  ```
- `pyproject.toml` `[project.dependencies]` (estilo `pyproject.toml:56-57`): `"pywebpush>=2.0.0,<3.0",` num comentário `# Web Push (VAPID)`.
- Instalar localmente para a suíte enxergar a dep: `uv pip install "pywebpush>=2.0.0,<3.0"` (o import de `pywebpush` só é exercitado na Sessão 32; aqui basta a declaração + install para o gate de tipos não acusar dep ausente).

### Documentação de env (`.env.example` e `.env.production.example`)
Adicionar uma seção (estilo `.env.example:142-156`) em **ambos** os arquivos:
```
# =============================================================================
# WEB PUSH (VAPID) — notificações push na web
# =============================================================================
# Gerar o par de chaves (uma única vez) com a CLI do py_vapid (vem com pywebpush):
#   vapid --gen            # gera private_key.pem + public_key.pem no diretório atual
#   vapid --applicationServerKey   # imprime a chave pública em base64url (use no front)
# Cole a chave pública (base64url) em VAPID_PUBLIC_KEY e a privada em VAPID_PRIVATE_KEY.
# VAPID_SUBJECT deve ser um mailto: do responsável.
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:admin@example.com
```
- No `.env.production.example`, usar o mesmo bloco (sem valores reais; comentário de "gerar uma única vez e guardar no secret manager").

### Migração
- Rodar `python manage.py makemigrations core` → gera `core/migrations/0044_webpushsubscription.py` (1 operação `CreateModel`).
- **Backup ANTES** de qualquer `migrate` (regra `.claude/rules/database.md`): `python scripts/backup_db.py`.
- Aplicar com `python manage.py migrate core` após o backup. Conferir reversibilidade: `python manage.py migrate core 0043` desfaz e `migrate core` reaplica (testar forward/back uma vez).

## TDD

Rodar **somente o arquivo de teste desta sessão** (`tests/unit/test_web_push_model.py`). A suíte completa tem
problemas pré-existentes de xdist/Redis — ver memória do projeto; **não** rodar a suíte inteira.

### 1. Red — escrever os testes primeiro (devem falhar: `WebPushSubscription` não existe)
Comando (deve falhar): `python -m pytest tests/unit/test_web_push_model.py -v`

Importar `WebPushSubscription` de `core.models`; marcar a classe/funções com `@pytest.mark.django_db`
(model toca o banco). Usar a fixture `regular_user` (`conftest.py:80-92`) para a FK. Cobrir **exatamente**
estes cenários (um teste por bullet):

- **Cria com campos válidos**: `WebPushSubscription.objects.create(user=regular_user, endpoint="https://push.example/abc", p256dh="pkey", auth="akey")` retorna `pk` não-nulo e persiste os 4 campos.
- **`is_active` default True**: criar **sem** passar `is_active` → instância tem `is_active is True`.
- **`endpoint` é unique (IntegrityError em duplicado)**: criar duas inscrições com o **mesmo** `endpoint` levanta `django.db.utils.IntegrityError` (usar `pytest.raises(IntegrityError)` dentro de `transaction.atomic()` para não envenenar a transação do teste).
- **`__str__`**: `str(sub)` retorna exatamente `f"Web push for {regular_user}"`.
- **`related_name` funciona**: após criar a inscrição, `regular_user.web_push_subscriptions.count() == 1` e `regular_user.web_push_subscriptions.first()` é a inscrição criada.
- **Herda `AuditMixin` (sem SoftDelete)**: a instância tem `created_at`/`updated_at` não-nulos; e **não** tem `is_deleted` (assert `not hasattr(sub, "is_deleted")`) — confirma que `SoftDeleteMixin` **não** foi herdado.

### 2. Green — implementar o mínimo para passar
- Adicionar a classe `WebPushSubscription` em `core/models.py` (espec acima).
- `python manage.py makemigrations core` → revisar o diff da migração `0044_*` (1 `CreateModel`, sem ops inesperadas).
- **Backup** (`python scripts/backup_db.py`) e então `python manage.py migrate core`.
- Adicionar as 3 settings VAPID em `settings.py`, a dep nos 2 arquivos, e a doc de env nos 2 `.env.*.example`.

### 3. Refactor — sem mudanças de comportamento
- Conferir que o model não introduziu `Meta` desnecessário, comentários supérfluos ou docstring redundante (KISS/DRY). Posição correta (após `DeviceToken`, antes de `PaymentProof`).

### 4. Verify (gate do projeto — backend)
- `python -m pytest tests/unit/test_web_push_model.py -v` → tudo verde.
- `ruff check && ruff format --check` → zero erros/avisos.
- `mypy core/` → zero erros (no model e settings tocados).
- `pyright` → zero erros/avisos.
- Conferir `python manage.py makemigrations core --check --dry-run` → "No changes detected" (migração já aplicada/commitada; sem migração pendente esquecida).

## Constraints (NÃO fazer)
- **NÃO** tocar em `core/services/notification_service.py` — extrair `send_expo_push`/`send_web_push` e o envio unificado é a **Sessão 32**.
- **NÃO** criar `WebPushViewSet`, nem registrar rotas em `core/urls.py`/`core/viewsets/__init__.py`, nem serializer — tudo isso é a **Sessão 32**.
- **NÃO** herdar `SoftDeleteMixin` no model (espelhar `DeviceToken`).
- **NÃO** editar migrações existentes (`migrations/0*.py`) — o hook bloqueia; criar a nova via `makemigrations` e **não** hardcodar o número 0044 em código/docs além do nome do arquivo gerado.
- **NÃO** rodar `migrate` destrutivo sem `python scripts/backup_db.py` antes (regra `.claude/rules/database.md`). Esta migração só **cria** tabela (não-destrutiva), mas o backup permanece obrigatório por política.
- **NÃO** adicionar a dep em só um arquivo — `pywebpush` vai em `requirements.txt` **E** `pyproject.toml` (regra `.claude/rules/coding-standards.md`).
- **NÃO** usar `try/except ImportError` / flags `HAS_*` para o `pywebpush` (regra: sem deps opcionais). O import só aparece na Sessão 32, importado direto no topo.
- **NÃO** usar `from __future__ import annotations` (PEP 649 nativo no Python 3.14).
- **NÃO** usar `# noqa` / `# type: ignore` / `eslint-disable` / `@ts-ignore` — corrigir na raiz.
- **NÃO** mockar internals (ORM/model/Django) — o teste de model usa **banco real** (`--reuse-db`), conforme `tests/CLAUDE.md`. Nada a mockar nesta sessão (sem boundary externo; `pywebpush` não é exercitado aqui).
- **NÃO** rodar a suíte completa (apenas `tests/unit/test_web_push_model.py`) — evitar falhas pré-existentes de xdist/Redis.
- SOLID/DRY/KISS/YAGNI — model de responsabilidade única, sem `Meta`/índices especulativos, sem re-export/barrel.

## Critérios de Aceite
- [ ] `core/models.py` tem `class WebPushSubscription(AuditMixin, models.Model)` com `user` (FK `related_name="web_push_subscriptions"`, `on_delete=CASCADE`), `endpoint` (`TextField(unique=True)`), `p256dh`/`auth` (`CharField(max_length=255)`), `is_active` (`BooleanField(default=True)`), e `__str__` → `f"Web push for {self.user}"`.
- [ ] Model **não** herda `SoftDeleteMixin` (espelha `DeviceToken`); posicionado após `DeviceToken`, antes de `PaymentProof`.
- [ ] Migração `core/migrations/0044_webpushsubscription.py` gerada por `makemigrations` (1 `CreateModel`), aplicada, e reversível; `makemigrations --check --dry-run` reporta "No changes detected".
- [ ] **Backup** (`python scripts/backup_db.py`) executado antes do `migrate` (evidência no handoff).
- [ ] `settings.py` define `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` (default `""`) e `VAPID_SUBJECT` (default `mailto:admin@example.com`) via `config(...)`, após o bloco Twilio.
- [ ] `pywebpush>=2.0.0,<3.0` consta em `requirements.txt` **e** `pyproject.toml` `[project.dependencies]`.
- [ ] `.env.example` **e** `.env.production.example` documentam as 3 vars VAPID + o comando de geração (`vapid --gen` / `vapid --applicationServerKey`).
- [ ] `tests/unit/test_web_push_model.py` cobre: cria; `is_active` default True; `endpoint` unique (`IntegrityError`); `__str__`; `related_name`; herança `AuditMixin` sem `is_deleted`. 100% verde.
- [ ] `ruff check && ruff format --check`, `mypy core/`, `pyright` — zero erros/avisos.
- [ ] `notification_service.py`, `core/urls.py`, `core/viewsets/` **inalterados** nesta sessão.
- [ ] Sem `# noqa`/`# type: ignore`; sem `try/except ImportError`; sem `from __future__ import annotations`; sem re-exports.

## Handoff
1. Rodar e confirmar verde (colar saída como evidência):
   - `python -m pytest tests/unit/test_web_push_model.py -v`
   - `ruff check && ruff format --check`
   - `mypy core/`
   - `pyright`
   - `python manage.py makemigrations core --check --dry-run` (esperar "No changes detected")
2. Registrar a evidência do **backup** (`python scripts/backup_db.py`) executado antes do `migrate`.
3. Atualizar `prompts/SESSION_STATE.md`: abrir a feature "App Mobile Completo (PWA/Offline/Web Push)" (design `docs/plans/2026-06-04-mobile-pwa-offline-design.md`); marcar **Sessão 31 concluída**; listar arquivos criados (`tests/unit/test_web_push_model.py`, `core/migrations/0044_webpushsubscription.py`) e modificados (`core/models.py`, `condominios_manager/settings.py`, `requirements.txt`, `pyproject.toml`, `.env.example`, `.env.production.example`); anotar que a **Sessão 32** fará o `notification_service` (refactor + `send_web_push`) e o `WebPushViewSet`/rotas, **consumindo** este model e estas settings sem alterá-los.
4. Commit (não usar a branch default sem antes ramificar; commitar só quando solicitado):
   ```
   feat(backend): add WebPushSubscription model, VAPID settings and pywebpush dep

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
5. A Sessão 32 começa lendo o `SESSION_STATE.md`.
