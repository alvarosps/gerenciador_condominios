# Plano P1.4 — Hardening de auth diversos (upload, enumeração OTP, OAuth, senha)

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P1 · **Branch sugerida:** `fix/auth-hardening` · **Depende de:** P0.1

## Objetivo

Endurecer cinco superfícies de autenticação/upload sem refatoração profunda: validar o conteúdo real do upload de comprovante PIX (magic bytes + extensão, não só o `content_type` forjável do cliente), eliminar a enumeração de CPF nos endpoints OTP de WhatsApp respondendo de forma genérica idêntica, parar de persistir indefinidamente tokens JWT em texto plano no `OAuthExchangeCode`, tornar o exchange de código OAuth atômico, e aplicar os validadores de senha do Django (`AUTH_PASSWORD_VALIDATORS`) nos dois fluxos de mudança de senha. Tudo isso reduz exposição de PII/LGPD e endurece o portal do inquilino e o login admin que já rodam em produção.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MÉDIO | `PaymentProofSerializer.validate_file` valida só `content_type` do cliente (forjável) | `core/serializers.py:1273-1282` | Validar magic bytes (Pillow p/ imagem, header `%PDF-`) + extensão; servir com `nosniff` + `Content-Disposition: attachment` |
| MÉDIO | Enumeração de CPF: `request_code`/`verify_code` retornam 404 "Inquilino não encontrado" | `core/viewsets/auth_views.py:77-78, 135-136` | Resposta genérica 200 idêntica ("se cadastrado, código enviado"); manter rate limit |
| MÉDIO | `OAuthExchangeCode` guarda access/refresh em texto plano e nunca é purgado | `core/models.py:1771-1796`; `core/auth.py:153-154` | Deletar a linha após uso bem-sucedido + purge de expirados no mesmo fluxo |
| BAIXO | `exchange_oauth_code` não atômico | `core/auth.py:145-154` | Envolver lookup→consumo em `transaction.atomic()` + `select_for_update()` |
| BAIXO | `change_password`/`set_password` não aplicam `validate_password` do Django | `core/viewsets/profile_views.py:109`; `core/viewsets/auth_views.py:218` | Chamar `django.contrib.auth.password_validation.validate_password(senha, user)` |
| BAIXO | Template de contrato `{{ regra \| safe }}` (HTML do admin) sem sanitização | `core/templates/contract_template.html:645` | Sanitizar `ContractRule.text` no service com allowlist (`nh3`) antes de passar ao template |

## Abordagem técnica

Ordem de execução pensada para isolar cada achado (cada um com seu RED→GREEN). Cada bloco abaixo é independente; podem ser commits separados na mesma branch.

### 1. Upload de comprovante — validação de conteúdo real (MÉDIO)

Arquivo: `core/serializers.py`, método `PaymentProofSerializer.validate_file` (linhas 1273-1282). Hoje só checa `value.size` e `value.content_type` (header do multipart, forjável pelo cliente).

- Extrair um validador stateless reutilizável em `core/validators/upload.py` (novo módulo): função `validate_proof_file(uploaded_file)` que:
  1. Mantém o limite de 10MB (constante `_MAX_PROOF_SIZE_BYTES = 10 * 1024 * 1024`).
  2. Valida a **extensão** do `uploaded_file.name` contra um allowlist `{".jpg", ".jpeg", ".png", ".pdf"}` (lowercase via `pathlib.Path(name).suffix.lower()`).
  3. Valida os **magic bytes** lendo o início do arquivo sem consumir o ponteiro: ler `header = uploaded_file.read(8); uploaded_file.seek(0)`. Para PDF, `header.startswith(b"%PDF-")`. Para imagem, abrir com Pillow `PIL.Image.open(uploaded_file)` dentro de `try/except (UnidentifiedImageError, OSError)` e checar `img.format in {"JPEG", "PNG"}`; sempre `uploaded_file.seek(0)` no `finally` para não corromper o `save()` subsequente.
  4. Exige consistência extensão↔conteúdo: extensão `.pdf` deve casar com header PDF; `.jpg/.jpeg/.png` deve casar com `img.format` correspondente. Mismatch → `ValidationError`.
  - Pillow já está em `requirements.txt:40` (`Pillow>=11.0.0`) — importar `from PIL import Image, UnidentifiedImageError` direto no topo do módulo (regra do projeto proíbe `try/except ImportError`).
  - Mensagens em PT-BR para o usuário: "Tipo de arquivo não permitido. Use JPEG, PNG ou PDF." (mantém a string atual) e "Conteúdo do arquivo não corresponde à extensão." para mismatch.
- `PaymentProofSerializer.validate_file` passa a delegar a `validate_proof_file(value)` e retornar `value`. Remover a lógica inline antiga (sem deixar `content_type` como única defesa).
- **Servir com defesa em profundidade:** adicionar `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` na resposta que serve o arquivo do comprovante. O serve atual é genérico (`condominios_manager/urls.py:96`, `django.views.static.serve` em `^media/`), que não permite per-file header e em prod serve o diretório inteiro. Como P0.1 (dependência) trata da exposição pública de `contracts/`/`media`, **este plano apenas garante** que, quando um comprovante for servido por um endpoint DRF autenticado (criado em P0.1, mesmo padrão de `TenantViewSet.contract` em `tenant_views.py:137-177` que retorna `FileResponse`), a resposta carregue `response["Content-Disposition"] = "attachment; filename=..."` e `response["X-Content-Type-Options"] = "nosniff"`. Se P0.1 ainda não tiver migrado o serve do comprovante para um endpoint autenticado, criar aqui um `@action(detail=False, url_path=r"payments/proof/(?P<proof_id>\d+)/file")` em `TenantViewSet` que valida ownership (mesmo padrão de `payments_proof_status`, `tenant_views.py:348-381`) e retorna `FileResponse(..., as_attachment=True)` com o header nosniff. Não usar `django.views.static.serve` para comprovantes.

### 2. Enumeração de CPF nos endpoints OTP (MÉDIO)

Arquivo: `core/viewsets/auth_views.py`. Hoje ambos os endpoints revelam quem é inquilino:
- `request_code` (linhas 56-106): em `Tenant.DoesNotExist` retorna 404 "Inquilino não encontrado" (linha 77-78).
- `verify_code` (linhas 108-189): idem em `Tenant.DoesNotExist` (linha 135-136); e responde 404 "Nenhuma verificação pendente encontrada" (147-150), que também distingue.

Correção (manter o rate limit `VerificationRateThrottle` intacto):

- **`request_code`:** mover o `Tenant.objects.get` para dentro de um caminho que **sempre** retorna a mesma resposta genérica 200, independentemente de o tenant existir. Quando o tenant existe e o rate limit não estourou, criar a `WhatsAppVerification` e disparar `send_verification_code` como hoje; quando não existe, **não** criar nada nem enviar, mas retornar a **mesma** resposta. Resposta única: `Response({"detail": "Se o CPF/CNPJ estiver cadastrado, um código foi enviado via WhatsApp."}, status=200)`. O rate-limit por `cpf_cnpj` (linhas 80-90) continua e ainda pode devolver 429 (isso não enumera inquilino — qualquer CPF pode estourar a janela; manter, pois é o limite de envio). A validação de `cpf_cnpj` vazio (linha 72-73) continua 400.
- **`verify_code`:** o caminho de sucesso depende de `tenant` existir e ter `verification` válida. Para não enumerar: tratar "tenant não encontrado" e "nenhuma verificação pendente"/"código inválido" com a **mesma** resposta 400 genérica `{"error": "Código inválido."}` (já existe essa string na linha 167). Concretamente: substituir o 404 "Inquilino não encontrado" (135-136) por `tenant = Tenant.objects.filter(cpf_cnpj=cpf_cnpj).first()`; se `tenant is None`, cair no mesmo retorno 400 "Código inválido." que um código errado. Substituir o 404 "Nenhuma verificação pendente encontrada" (147-150) por 400 "Código inválido.". Os caminhos de bloqueio por tentativas (429, 152-156) e expirado (158-162) podem permanecer, pois só são alcançáveis por quem já tem uma verificação pendente real (não vazam quem é inquilino — exigem ter pedido código antes). **Não** alterar a lógica de incremento de `attempts`/`is_used`/criação de `User` dentro do `transaction.atomic()` (138-180).
- Logs: manter `logger.info` em EN; não logar se o CPF existe ou não de forma que vaze (o log atual em 104 já loga o cpf solicitado — aceitável, é log interno).

### 3. OAuthExchangeCode — não persistir tokens após uso + purge (MÉDIO) e exchange atômico (BAIXO)

Arquivo: `core/auth.py`, função `exchange_oauth_code` (linhas 130-181). Hoje: `OAuthExchangeCode.objects.get(code=code)` (146), `is_used=True; save` (153-154), e a linha persiste para sempre com `access_token`/`refresh_token` legíveis (`core/models.py:1780-1781`).

- Envolver o consumo em `with transaction.atomic():` e usar `select_for_update()` no lookup para serializar trocas concorrentes do mesmo código: `exchange = OAuthExchangeCode.objects.select_for_update().get(code=code)`. Manter o `except (OAuthExchangeCode.DoesNotExist, ValueError)` (147-148) — `ValueError` cobre UUID malformado.
- Dentro do bloco atômico, após validar `is_valid()` e `is_staff`, **ler os tokens para variáveis locais** (`access = exchange.access_token; refresh = exchange.refresh_token`), montar a `Response`, chamar `_set_auth_cookies(response, access, refresh)` com as variáveis locais (não mais com `exchange.access_token`), e então **deletar a linha**: `exchange.delete()` (hard delete — `OAuthExchangeCode` não usa `SoftDeleteMixin`, confirmado em `models.py:1771`). Remover o `is_used=True; save` (153-154) — a deleção torna o código não reutilizável de forma definitiva e elimina o material sensível do banco.
- **Purge de expirados:** no mesmo fluxo (antes do retorno, ainda barato), executar `OAuthExchangeCode.objects.filter(created_at__lt=timezone.now() - timedelta(seconds=OAuthExchangeCode.TTL_SECONDS)).delete()`. Importar `from datetime import timedelta` e `from django.utils import timezone` no topo de `core/auth.py`. Isso garante que códigos abandonados (gerados mas nunca trocados) não acumulem tokens. Adicionar método de classe `OAuthExchangeCode.purge_expired()` em `core/models.py` encapsulando esse delete (Clean Code: lógica de negócio no model é aceitável para housekeeping simples e mantém DRY caso um cron futuro reuse — mas **não** criar cron novo neste plano, YAGNI).
- O caso de `is_used` na branch de erro (model `is_valid` ainda checa `is_used`, `models.py:1793`) continua coerente: como agora deletamos em vez de marcar, um segundo POST com o mesmo código cai em `DoesNotExist` → 400 "Invalid or expired code". O campo `is_used` permanece no model (usado por `is_valid` e por testes existentes), mas deixa de ser escrito pelo fluxo de exchange. **Não** remover a coluna `is_used` (evita migration desnecessária e mantém `GoogleOAuthCallbackView` e testes consistentes).
- **Regressão de teste existente:** `tests/unit/test_auth.py:153-154` (`test_valid_unused_code_returns_200_and_sets_cookies`) faz `exchange.refresh_from_db(); assert exchange.is_used is True`. Com a deleção, `refresh_from_db` levantará `DoesNotExist`. Atualizar esse teste para assertir que a linha **deixou de existir**: `assert not OAuthExchangeCode.objects.filter(pk=exchange.pk).exists()`. O teste `test_already_used_code_returns_400` (160-166) continua válido (linha já consumida = inexistente para o novo fluxo; ajustar para criar e deletar, ou manter setando `is_used=True` já que `is_valid` ainda o respeita — manter como está pois `is_valid` segue checando `is_used`).

### 4. validate_password do Django nos dois fluxos de senha (BAIXO)

`AUTH_PASSWORD_VALIDATORS` já está configurado (`settings.py:165-178`: UserAttributeSimilarity, MinimumLength, CommonPassword, NumericPassword), mas nenhum dos fluxos de senha o usa.

- **`change_password`** (`core/viewsets/profile_views.py:76-119`): hoje só checa `len(new_password) < 8` (109). Substituir essa checagem por `validate_password(new_password, user)` de `django.contrib.auth.password_validation`, capturando `django.core.exceptions.ValidationError` e devolvendo 400 com as mensagens: `return Response({"error": " ".join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)`. Manter a checagem de campos obrigatórios (97-101) e de senha atual (103-107). Remover a constante `_MIN_PASSWORD_LENGTH` se ficar órfã (o `MinimumLengthValidator` já cobre o mínimo — KISS/DRY).
- **`set_password`** (`core/viewsets/auth_views.py:204-229`): hoje só checa `len(password) < 8` (218). Substituir por `validate_password(password, user)` (o `user` é `request.user`, `cast(User, ...)` na linha 224 — mover o cast para antes da validação). Capturar `DjangoValidationError` e devolver 400 com `e.messages` juntados. Remover/ajustar a constante `_MIN_PASSWORD_LENGTH` (linha 42) se ficar órfã.
- Importar no topo de cada arquivo: `from django.contrib.auth.password_validation import validate_password` e `from django.core.exceptions import ValidationError as DjangoValidationError`. As mensagens dos validadores do Django são em EN por padrão; como `LANGUAGE_CODE = "en-us"` (settings.py:184), as mensagens sairão em EN — aceitável para este escopo (validador de segurança; o frontend pode mapear). **Não** introduzir tradução de catálogo i18n neste plano (YAGNI).

### 5. Sanitização do template de contrato (BAIXO)

`core/templates/contract_template.html:645` renderiza `{{ regra | safe }}` para cada regra. As regras vêm de `ContractService` (`core/services/contract_service.py:198-216`): `db_rules = ContractRule.get_active_rules()` (texto editável pelo admin) com fallback para `regras_condominio` hardcoded. Como o admin pode digitar HTML arbitrário, `| safe` permite stored XSS no PDF/preview.

- Sanitizar no **service** (camada correta — lógica de negócio), não no template. No `contract_service.py`, antes de montar o dict de contexto (`"rules": rules`, linha 216), passar cada regra por um sanitizador allowlist usando `nh3` (binding Rust do ammonia, manutenção ativa em 2026; alternativa: `bleach` está deprecado). Função helper `_sanitize_rule(text: str) -> str` que chama `nh3.clean(text, tags={"b","i","strong","em","br"}, attributes={})` permitindo só formatação inline básica e removendo `<script>`, `<a>`, `on*=`, etc. Aplicar via list-comprehension: `rules = [_sanitize_rule(r) for r in (db_rules or regras_condominio)]`.
- O template **mantém** `| safe` (agora o conteúdo já está sanitizado pelo service — fonte única de verdade da sanitização na camada de negócio).
- **Dependência nova:** adicionar `nh3>=0.2,<0.3` em `requirements.txt`, em `pyproject.toml` `[project.dependencies]` (regra do projeto: dependência em todos os lugares), e importar `import nh3` direto no topo de `contract_service.py` (sem `try/except ImportError`). Se `nh3` não puder ser adicionado no ambiente, fallback aceitável: escapar tudo com `django.utils.html.escape` e **remover** o `| safe` do template (perde formatação inline mas é seguro e sem dependência nova) — decidir no início da execução; preferir `nh3` para preservar a formatação que o admin espera.

## Arquivos a criar / modificar

- `core/validators/upload.py` — **criar**: `validate_proof_file(uploaded_file)` (magic bytes Pillow + header `%PDF-` + extensão + tamanho). Constantes de allowlist e tamanho.
- `core/serializers.py` — **modificar**: `PaymentProofSerializer.validate_file` (1273-1282) delega ao novo validador.
- `core/viewsets/auth_views.py` — **modificar**: `request_code` (resposta genérica 200) e `verify_code` (sem 404 de tenant/verificação; cai em 400 "Código inválido."); aplicar `validate_password` em `SetPasswordViewSet.set_password`; ajustar/remover `_MIN_PASSWORD_LENGTH`.
- `core/viewsets/profile_views.py` — **modificar**: `change_password` usa `validate_password`; ajustar/remover `_MIN_PASSWORD_LENGTH`.
- `core/auth.py` — **modificar**: `exchange_oauth_code` atômico + `select_for_update` + delete pós-uso + `purge_expired`; novos imports `timedelta`/`timezone`.
- `core/models.py` — **modificar**: adicionar `OAuthExchangeCode.purge_expired()` classmethod.
- `core/services/contract_service.py` — **modificar**: `_sanitize_rule` + sanitizar `rules` antes do contexto; `import nh3`.
- `core/viewsets/tenant_views.py` — **modificar** (se P0.1 não cobriu): action que serve o arquivo do comprovante com `as_attachment=True` + header `X-Content-Type-Options: nosniff`.
- `requirements.txt` + `pyproject.toml` — **modificar**: adicionar `nh3` (e confirmar `Pillow` já presente).
- `core/templates/contract_template.html` — **inalterado** (mantém `| safe`; conteúdo já sanitizado no service).
- **Testes** (criar/modificar):
  - `tests/unit/test_proof_upload_validation.py` — **criar**: cenários de magic bytes/extensão.
  - `tests/integration/test_tenant_auth_api.py` — **modificar**: cenários de não-enumeração (request/verify).
  - `tests/unit/test_auth.py` — **modificar**: ajustar `test_valid_unused_code_returns_200_and_sets_cookies` (linha exclui em vez de `is_used`); adicionar cenários de atomicidade/purge.
  - `tests/integration/test_password_change_api.py` — **criar**: `validate_password` em ambos os fluxos.
  - `tests/unit/test_contract_rule_sanitization.py` — **criar**: sanitização de regra com HTML malicioso.

## TDD — cenários de teste

Upload (`tests/unit/test_proof_upload_validation.py`):
- `test_valid_jpeg_passes` — arquivo JPEG real (Pillow gera bytes) com `.jpg` passa.
- `test_valid_png_passes` — PNG real com `.png` passa.
- `test_valid_pdf_passes` — bytes iniciando com `%PDF-` e `.pdf` passam.
- `test_forged_content_type_pdf_with_html_body_rejected` — `content_type="application/pdf"` mas corpo é HTML/texto → rejeitado (prova do bug: hoje passaria).
- `test_extension_mismatch_png_bytes_jpg_name_rejected` — bytes PNG com nome `.jpg` → rejeitado (consistência extensão↔conteúdo).
- `test_disallowed_extension_exe_rejected` — `.exe` → rejeitado mesmo com bytes de imagem.
- `test_oversize_file_rejected` — > 10MB → rejeitado (mantém regra).
- `test_file_pointer_reset_after_validation` — após validar, `file.read()` retorna o conteúdo completo (garante `seek(0)`).

Enumeração OTP (`tests/integration/test_tenant_auth_api.py`):
- `test_request_code_unknown_cpf_returns_generic_200` — CPF inexistente → 200 com a **mesma** mensagem genérica de quando existe; nenhum `WhatsAppVerification` criado; `send_verification_code` não chamado (mock no boundary).
- `test_request_code_known_cpf_returns_same_generic_200` — CPF existente → 200 com a **mesma** string; verificação criada e envio chamado.
- `test_verify_unknown_cpf_returns_400_generic` — CPF inexistente → 400 "Código inválido." (igual a código errado), nunca 404.
- `test_verify_known_cpf_no_pending_returns_400_generic` — CPF existente sem verificação pendente → 400 "Código inválido." (não 404 "Nenhuma verificação pendente").
- `test_verify_happy_path_still_returns_tokens` — regressão: fluxo correto (request→verify com código certo) ainda devolve `{access, refresh}` 200.
- `test_request_rate_limit_still_enforced` — 4ª chamada para o mesmo CPF existente → 429 (rate limit preservado).

OAuth exchange (`tests/unit/test_auth.py`):
- `test_valid_unused_code_returns_200_and_deletes_row` — (substitui o antigo) 200, cookies setados, e `OAuthExchangeCode.objects.filter(pk=...).exists() is False`.
- `test_reused_code_after_success_returns_400` — segundo POST com o mesmo código (já deletado) → 400 "Invalid or expired code".
- `test_expired_unused_codes_are_purged_on_exchange` — cria uma linha expirada (>60s via freezegun) + uma válida; ao trocar a válida, a expirada é deletada (`purge_expired`).
- `test_purge_expired_classmethod_deletes_only_old` — unit do classmethod: linha recente sobrevive, linha antiga some.
- `test_non_admin_code_returns_403_and_does_not_leak_tokens` — regressão: não-staff → 403 (e, idealmente, código consumido/deletado para não vazar — decidir: deletar mesmo no 403 para não deixar tokens; **incluir** cenário assertindo deleção também no 403).

Senha (`tests/integration/test_password_change_api.py`):
- `test_change_password_too_short_returns_400` — nova senha < 8 → 400 (MinimumLengthValidator).
- `test_change_password_too_common_returns_400` — "password123" / "12345678" → 400 (CommonPassword/NumericPassword).
- `test_change_password_similar_to_username_returns_400` — senha = username/email → 400 (UserAttributeSimilarity).
- `test_change_password_strong_succeeds` — senha forte → 200 e login com nova senha funciona (regressão de fluxo).
- `test_change_password_wrong_old_returns_400` — regressão: senha atual errada ainda 400 antes de validar a nova.
- `test_set_password_weak_returns_400` / `test_set_password_strong_succeeds` — idem para `SetPasswordViewSet` (admin).

Sanitização (`tests/unit/test_contract_rule_sanitization.py`):
- `test_script_tag_stripped_from_rule` — regra `"<script>alert(1)</script>Pague em dia"` → contexto sem `<script>`.
- `test_event_handler_attribute_stripped` — `"<b onclick=...>x</b>"` → `onclick` removido, `<b>` preservado.
- `test_allowed_inline_formatting_preserved` — `<strong>`/`<em>`/`<br>` preservados.
- `test_anchor_tag_removed` — `<a href=...>` removido (não está no allowlist).
- `test_plain_rule_unchanged` — regra sem HTML passa intacta (regressão).

## Migrations / dados

N/A — nenhuma alteração de schema. Não se cria tabela nova (logo, sem `RLS`). `OAuthExchangeCode.is_used` permanece (sem migration). O `purge_expired` apenas deleta linhas de `core_oauth_exchange_code` em runtime; é housekeeping de dados transitórios (TTL 60s), **não** dado financeiro — não requer backup. Confirmar mesmo assim que nenhum `migrate` destrutivo é gerado por engano após editar `core/models.py` (adicionar classmethod não gera migration; rodar `python manage.py makemigrations --check` e esperar "No changes").

## Constraints (o que NÃO fazer)

- Não remover a coluna `OAuthExchangeCode.is_used` nem criar migration para isso — `is_valid()` e testes ainda a usam; só parar de escrevê-la no exchange.
- Não enfraquecer nem remover `VerificationRateThrottle` ao corrigir a enumeração — o 429 por rate limit permanece.
- Não tocar no módulo financeiro pessoal legado, nem refatorar serializers/views além do estritamente necessário para os cinco achados.
- Não usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `from __future__ import annotations`, nem `try/except ImportError` para Pillow/nh3 (importar direto no topo).
- Não mockar internals (ORM, serializers, services, validadores próprios). Mockar só fronteiras: `send_verification_code` (HTTP Twilio) e, se necessário, o serve de arquivo. Pillow roda real sobre bytes reais gerados em memória.
- Não traduzir as mensagens dos validadores de senha do Django neste plano (i18n é fora de escopo — YAGNI).
- Não criar cron de purge neste plano (apenas purge oportunista no exchange) — cron é YAGNI aqui.
- Não alterar `contract_template.html` além de manter o `| safe` (a sanitização vai no service).
- Sobreposição com P0.1: se P0.1 já moveu o serve do comprovante para endpoint autenticado, **não** duplicar — apenas adicionar os headers `attachment`/`nosniff` lá. Confirmar o estado de P0.1 antes de criar a action de serve.

## Critérios de aceite (binários)

- [ ] `validate_proof_file` rejeita arquivo com `content_type` PDF forjado mas corpo não-PDF, e rejeita mismatch extensão↔conteúdo; aceita JPEG/PNG/PDF reais; ponteiro do arquivo intacto após validação.
- [ ] `request_code` retorna **a mesma** resposta 200 genérica para CPF existente e inexistente; nenhum `WhatsAppVerification` é criado para CPF inexistente.
- [ ] `verify_code` nunca retorna 404 de "Inquilino não encontrado"/"Nenhuma verificação pendente"; CPF inexistente e código errado retornam a **mesma** 400 "Código inválido.".
- [ ] Fluxo OTP feliz (request→verify com código correto) ainda devolve `{access, refresh}` e cria o `User` do tenant.
- [ ] Rate limit OTP (429) preservado.
- [ ] `exchange_oauth_code` executa dentro de `transaction.atomic()` com `select_for_update()`; após sucesso a linha `OAuthExchangeCode` é deletada (`.exists()` == False) e os tokens não permanecem no banco.
- [ ] Códigos expirados são purgados ao trocar um código válido; `purge_expired()` deleta só os antigos.
- [ ] `change_password` e `set_password` rejeitam senha curta/comum/numérica/similar-ao-usuário (via `validate_password`) com 400; senha forte é aceita.
- [ ] Regras de contrato com `<script>`/`on*=`/`<a>` são sanitizadas no service; formatação inline allowlisted preservada; regra sem HTML intacta.
- [ ] `python manage.py makemigrations --check` reporta "No changes" (nenhuma migration acidental).
- [ ] `nh3` (e `Pillow`) presentes em `requirements.txt` e `pyproject.toml`.

## Gate de verificação

Escopado nos arquivos editados + regressão dirigida (suite cheia tem flakiness pré-existente de xdist/Redis — não é bloqueio):

```bash
# Lint/type só do que mudou + módulos tocados
ruff check core/validators/upload.py core/serializers.py core/viewsets/auth_views.py core/viewsets/profile_views.py core/auth.py core/models.py core/services/contract_service.py core/viewsets/tenant_views.py
ruff format --check core/validators/upload.py core/serializers.py core/viewsets/auth_views.py core/viewsets/profile_views.py core/auth.py core/models.py core/services/contract_service.py core/viewsets/tenant_views.py
mypy core/
pyright

# Testes escopados nos achados (não rodar a suite cheia)
python -m pytest -p no:cacheprovider \
  tests/unit/test_proof_upload_validation.py \
  tests/integration/test_tenant_auth_api.py \
  tests/unit/test_auth.py \
  tests/integration/test_password_change_api.py \
  tests/unit/test_contract_rule_sanitization.py \
  tests/integration/test_admin_proofs_api.py

# Regressão dirigida: cookie auth + tenant API (consomem os fluxos tocados)
python -m pytest tests/integration/test_cookie_auth.py tests/integration/test_tenant_api.py
```

Zero erros E zero warnings em Ruff, mypy, Pyright e pytest nos arquivos escopados.

## Handoff

Commit sugerido (uma branch `fix/auth-hardening`, commits coesos por achado ou um único):

```
fix(auth): harden proof upload, OTP enumeration, OAuth token persistence and password rules

- validate proof upload by magic bytes (Pillow/%PDF) + extension, not client content_type
- serve proofs with attachment + nosniff
- generic identical responses on OTP request/verify (no CPF enumeration), keep rate limit
- delete OAuthExchangeCode after successful exchange + purge expired; wrap in atomic + select_for_update
- enforce Django validate_password in change_password and set_password
- sanitize ContractRule HTML in contract_service (nh3) before |safe render

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar `MEMORY.md` (entrada nova de auth-hardening) com: tokens OAuth não mais persistidos pós-exchange; endpoints OTP não enumeram; upload validado por conteúdo. O próximo plano (P1.x seguinte) pode assumir que: (a) o serve de comprovante carrega `nosniff`+`attachment`; (b) `OAuthExchangeCode` não retém material sensível; (c) qualquer novo fluxo de senha deve usar `validate_password`. Se P0.1 ainda não migrou o serve público de `contracts/`/`media`, registrar no handoff que o header `nosniff`/`attachment` foi adicionado no endpoint autenticado, mas o `django.views.static.serve` legado em `urls.py:96` continua dependente de P0.1.
