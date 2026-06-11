# Plano P2.2 — PIX EMV (acentos/bytes) + Twilio content_variables

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P2 · **Branch sugerida:** `fix/pix-emv-and-whatsapp` · **Depende de:** nenhum

## Objetivo

Corrigir dois bugs do portal mobile do inquilino (ativo, consumido por `mobile/` e `frontend/`), nao do modulo financeiro legado. Primeiro: a geracao de PIX EMV em `core/services/pix_service.py` quebra com nomes acentuados (Joao/Andre/default "Condominio") porque o CRC16 faz `data.encode("ascii")` (UnicodeEncodeError → 500 em `POST /api/tenant/payments/pix/`) e calcula o length TLV em caracteres em vez de bytes (payload EMV invalido), alem de fixar a cidade errada "Sao Paulo" para imoveis em Porto Alegre. Segundo: `core/services/whatsapp_service.py` passa `content_variables` como `dict` para o Twilio que exige string JSON — o codigo de verificacao e o aviso de reajuste chegam SEM os valores substituidos. A correcao destrava o login mobile (OTP via WhatsApp) e o pagamento PIX no caso comum brasileiro.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | `_crc16_ccitt` faz `data.encode("ascii")` → acento lanca UnicodeEncodeError → 500 no PIX | core/services/pix_service.py:10-21 | Sanitizar nome/cidade p/ ASCII antes do payload; CRC sobre bytes UTF-8/ASCII garantido |
| ALTO | `_emv_field` usa `len()` de caracteres, nao bytes → length TLV invalido | core/services/pix_service.py:24-26 | Calcular `len(value.encode("utf-8"))` (apos sanitizacao todos os campos sao ASCII puro) |
| ALTO | Cidade hardcoded "Sao Paulo" (imoveis em Porto Alegre) | core/viewsets/tenant_views.py:289 | Cidade configuravel via `Landlord.city` / `FinancialSettings`, resolvida em service |
| MEDIO→ALTO | `content_variables=dict` p/ Twilio que exige string JSON → variaveis nao substituidas | core/services/whatsapp_service.py:63-67 | `content_variables=json.dumps(template_variables)` |

## Abordagem técnica

Ordem de execucao (TDD Red→Green→Refactor→Verify em cada item):

### 1. Sanitizacao ASCII e length em bytes — `core/services/pix_service.py`

1. Adicionar `import unicodedata` no topo (logo apos `from decimal import Decimal`).
2. Criar funcao pura `_sanitize_ascii(value: str) -> str`:
   - `normalized = unicodedata.normalize("NFKD", value)`
   - `ascii_bytes = normalized.encode("ascii", "ignore")`
   - `return ascii_bytes.decode("ascii").upper()`
   - Spec BCB: campos `59` (merchant name) e `60` (city) devem ser ASCII, maiusculos. "Joao" → "JOAO", "Andre" → "ANDRE", "Condominio" → "CONDOMINIO", "Sao Paulo" → "SAO PAULO".
3. `_emv_field(tag, value)`: trocar `len(value)` por `len(value.encode("utf-8"))` para o length TLV em bytes. Apos a sanitizacao todos os valores que passam por aqui sao ASCII (1 byte/char), mas calcular em bytes e o correto pela spec e blinda contra qualquer valor nao sanitizado (ex.: `pix_key` email).
4. `_crc16_ccitt(data)`: o `data` que chega aqui ja sera 100% ASCII (todos os campos do payload sao numericos, ASCII fixos, ou ja sanitizados), entao `data.encode("ascii")` deixa de lancar. Manter `encode("ascii")` (semanticamente correto: EMV e ASCII) — a causa raiz e a falta de sanitizacao a montante, nao o encode em si. NAO trocar para `latin-1`/`utf-8` (mascararia o problema).
5. `generate_pix_emv`: aplicar sanitizacao no ponto de montagem dos campos `59` e `60`:
   - `_emv_field("59", _sanitize_ascii(merchant_name)[:25])`
   - `_emv_field("60", _sanitize_ascii(city)[:15])`
   - O slice `[:25]`/`[:15]` permanece APOS a sanitizacao (truncamento em caracteres ASCII = bytes, ok).
6. `generate_pix_payload`: assinatura inalterada (`pix_key, pix_key_type, amount, merchant_name, city`). O dict de retorno mantem `merchant_name` original (nao sanitizado) — e so metadata exibida; o EMV embutido em `pix_copy_paste`/`qr_data` ja usa a versao sanitizada. Manter como esta.

### 2. Cidade configuravel — resolucao no viewset + modelo

A cidade do recebedor PIX deve refletir o imovel real. Fonte de verdade:
1. `Landlord.city` JA EXISTE (`core/models.py:867`, `max_length=100`). Para o caminho default (condominio), usar `landlord.city` quando houver landlord ativo.
2. Para o caminho do owner (kitnet), nao existe cidade no `Person`/owner; usar a cidade do `Landlord` ativo como fallback unico de configuracao (o condominio e a referencia geografica). Se nao houver landlord, cair em `FinancialSettings` (novo campo, ver migration) e, por ultimo, num default de codigo `"Porto Alegre"`.
3. Em `core/viewsets/tenant_views.py` `payments_pix` (linhas 263-290), substituir a string fixa `city="Sao Paulo"` por uma cidade resolvida. Como a resolucao de recebedor (pix_key/merchant_name/city) e logica de negocio, NAO deve viver no viewset.

**Extracao para service (corrige tambem o achado de "logica de negocio em view"):** criar `core/services/pix_service.py::resolve_pix_recipient(lease: Lease) -> PixRecipient` (ou retornar `dict[str, str]` simples para KISS):
   - Recebe o `lease`, le `lease.apartment`, `apt.owner`, `FinancialSettings`, `Landlord.get_active()`.
   - Retorna `{"pix_key", "pix_key_type", "merchant_name", "city"}`.
   - Logica (espelha o viewset atual + cidade):
     - default: `merchant_name="Condomínio"`, `pix_key=""`, `pix_key_type=""`.
     - se `apt.owner and apt.owner.pix_key`: usa chave/tipo/nome do owner.
     - senao: le `FinancialSettings.objects.filter(pk=1).first()` para `default_pix_key`/`default_pix_key_type`; `Landlord.get_active()` para `merchant_name` (e `city`).
     - cidade: `landlord.city` se houver landlord ativo com city nao-vazia; senao `FinancialSettings.default_city` (novo campo) se nao-vazio; senao `"Porto Alegre"` (constante de modulo `_DEFAULT_CITY`).
   - O viewset passa a chamar `resolve_pix_recipient(lease)` e repassar para `generate_pix_payload(**recipient, amount=lease.rental_value)`. Mantem o `try/except ValueError → 400`.

   > Direcao de dependencia OK: service importa models; viewset → service → models. Service stateless (funcao pura sobre o lease). NAO importar service em serializer.

4. Novo campo `FinancialSettings.default_city` (ver Migrations). Opcional/blank, default `""`; quando vazio o service cai no `Landlord.city` ou no `_DEFAULT_CITY`.

### 3. Twilio content_variables como JSON — `core/services/whatsapp_service.py`

1. Adicionar `import json` no topo (antes de `import re`/`import secrets`, ordem ruff/isort).
2. Em `send_whatsapp_message` (linha 63-67), trocar:
   - `content_variables=template_variables` → `content_variables=json.dumps(template_variables)`.
3. `send_verification_code` e `send_rent_adjustment_notice` permanecem inalterados (ja passam `dict[str, str]` com chaves `"1"`, `"2"`...). A serializacao JSON acontece num unico ponto (DRY).
4. Nenhuma mudanca de assinatura publica.

## Arquivos a criar / modificar

- `core/services/pix_service.py` — MODIFICAR: `import unicodedata`; nova `_sanitize_ascii`; `_emv_field` length em bytes; `generate_pix_emv` sanitiza campos 59/60; nova `resolve_pix_recipient(lease)`; constante `_DEFAULT_CITY = "Porto Alegre"`.
- `core/viewsets/tenant_views.py` — MODIFICAR: `payments_pix` chama `resolve_pix_recipient(lease)` e remove a logica inline de resolucao + o `city="Sao Paulo"` hardcoded. Atualizar import (`from core.services.pix_service import generate_pix_payload, resolve_pix_recipient`).
- `core/services/whatsapp_service.py` — MODIFICAR: `import json`; `content_variables=json.dumps(template_variables)`.
- `core/models.py` — MODIFICAR: adicionar campo `default_city = models.CharField(max_length=100, blank=True, default="")` em `FinancialSettings`.
- `core/migrations/00XX_financialsettings_default_city.py` — CRIAR via `makemigrations` (AddField; sem RLS — tabela ja existe).
- `tests/unit/test_pix_service.py` — MODIFICAR: cenarios de acento, length em bytes, CRC valido, cidade sanitizada.
- `tests/unit/test_pix_recipient.py` — CRIAR: cenarios de `resolve_pix_recipient` (owner/default/landlord/financialsettings/fallback city). (banco real via pytest-django; usa model-bakery.)
- `tests/unit/test_whatsapp_service.py` — MODIFICAR: novo teste que mocka a fronteira `twilio.rest.Client` e assere `content_variables` recebido como string JSON.
- `tests/integration/test_tenant_api.py` — MODIFICAR: regressao do `payments_pix` com merchant acentuado (ex.: owner name "André") devolve 200 (nao 500) e `pix_copy_paste` valido.

## TDD — cenários de teste

PIX (`tests/unit/test_pix_service.py`):
- `test_merchant_name_with_accents_does_not_raise` — RED do bug: `generate_pix_emv(merchant_name="João", ...)` nao lanca UnicodeEncodeError e retorna string.
- `test_accented_name_sanitized_to_ascii_upper` — "João André" → payload contem "JOAO ANDRE" (sem acento, maiusculo).
- `test_default_condominio_name_works` — `merchant_name="Condomínio"` gera payload valido com "CONDOMINIO".
- `test_emv_field_length_is_bytes` — campo com valor ASCII tem length == numero de bytes; valor multibyte (caso `pix_key` email longo) usa contagem de bytes, nao de chars.
- `test_crc16_valid_for_accented_payload` — recalcular CRC sobre o payload (sem os 4 ultimos chars) bate com os 4 ultimos chars retornados (prova length+CRC corretos juntos).
- `test_city_sanitized` — `city="São Paulo"` → "SAO PAULO" no campo 60.
- Manter os 3 testes existentes (`test_generate_payload_with_cpf_key`, `test_generate_emv_format`, `test_no_pix_key_raises`) verdes.

Resolucao de recebedor (`tests/unit/test_pix_recipient.py`, banco real):
- `test_owner_pix_key_takes_precedence` — apartment com owner que tem `pix_key` → recipient usa chave/tipo/nome do owner.
- `test_falls_back_to_financialsettings_default_key` — sem owner key → usa `default_pix_key`/`default_pix_key_type` do `FinancialSettings`.
- `test_merchant_name_from_active_landlord` — sem owner → `merchant_name` = nome do `Landlord` ativo.
- `test_city_from_landlord` — `Landlord.city="Porto Alegre"` → recipient.city == "Porto Alegre".
- `test_city_from_financialsettings_when_no_landlord` — sem landlord, `FinancialSettings.default_city="Canoas"` → "Canoas".
- `test_city_falls_back_to_default_constant` — sem landlord e sem `default_city` → `_DEFAULT_CITY` ("Porto Alegre").

WhatsApp (`tests/unit/test_whatsapp_service.py`, mock SO da fronteira Twilio):
- `test_content_variables_sent_as_json_string` — patch de `twilio.rest.Client` (ou `core.services.whatsapp_service.Client`); chamar `send_whatsapp_message(to_phone, sid, {"1": "123456"})`; assertar que `messages.create` recebeu `content_variables='{"1": "123456"}'` (string, nao dict) e `json.loads()` reconstroi o dict.
- `test_missing_credentials_raises_runtimeerror` — sem `TWILIO_ACCOUNT_SID` (override_settings) → `RuntimeError`.
- `test_verification_code_uses_verification_template` — `send_verification_code` chama a fronteira com `content_sid=settings.TWILIO_TEMPLATE_VERIFICATION` e `content_variables` JSON contendo `{"1": code}`.
- Manter `TestNormalizePhone` e `TestGenerateCode` existentes verdes.

Integracao (`tests/integration/test_tenant_api.py`):
- `test_pix_with_accented_owner_name_returns_200` — owner name "André", `pix_key="andre@apto.com"` → `POST /api/tenant/payments/pix/` devolve 200 com `pix_copy_paste` nao-vazio (regressao do 500). Manter `test_owner_pix_key_used`, `test_missing_pix_key_returns_400`, `test_unauthenticated` verdes.

## Migrations / dados

- Migration nova `core/migrations/00XX_financialsettings_default_city.py` via `python manage.py makemigrations core` — `AddField` em `FinancialSettings.default_city` (CharField, blank, default `""`). NAO e tabela nova → **sem** RunSQL de RLS (RLS de `core_financialsettings` ja foi habilitado na 0047). `AddField` com default `""` e nao-destrutivo (sem `ALTER` que dropa/altera coluna existente), mas mesmo assim rodar `python scripts/backup_db.py` antes do `migrate` por politica.
- Reverse automatico (`RemoveField`) gerado pelo Django — sem RunSQL custom.
- Correcao de dado vivo: opcional/manual via admin — setar `FinancialSettings.default_city` ou `Landlord.city` em prod para a cidade real ("Porto Alegre"). NAO automatizar nesta migration (YAGNI; o fallback `_DEFAULT_CITY` ja cobre o caso vazio). Documentar no Handoff.

## Constraints (o que NÃO fazer)

- NAO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `from __future__ import annotations`, TODO/FIXME.
- NAO trocar `encode("ascii")` por `latin-1`/`utf-8` em `_crc16_ccitt` para "nao quebrar" — isso e workaround; a causa raiz e a sanitizacao ausente a montante.
- NAO mockar codigo interno nos testes: o teste do Twilio mocka SOMENTE `twilio.rest.Client` (fronteira externa); `send_whatsapp_message`/`send_verification_code`/`resolve_pix_recipient`/funcoes de pix rodam de verdade.
- NAO tocar no modulo financeiro legado (`Person/Expense/RentPayment/cash-flow/daily-control`) nem no app `finances/` — fora de escopo.
- NAO alterar o schema do mobile (campo `payload` vs `pix_copy_paste`) — e outro achado/plano; este plano NAO mexe em `mobile/`.
- NAO mudar a assinatura publica de `generate_pix_payload`/`generate_pix_emv`/`send_whatsapp_message` (mante-las estaveis para os callers existentes).
- NAO adicionar cidade ao `Person`/owner (YAGNI) — a cidade vem de `Landlord`/`FinancialSettings`.
- NAO refatorar o `payments_pix` alem de extrair a resolucao de recebedor para o service (manter o `try/except ValueError → 400`).

## Critérios de aceite (binários)

- [ ] `generate_pix_emv(merchant_name="João And.", city="São Paulo", ...)` retorna string e NAO lanca UnicodeEncodeError.
- [ ] Campos 59/60 do EMV ficam ASCII maiusculo sem acento ("JOAO", "SAO PAULO").
- [ ] Length TLV calculado em bytes (`len(value.encode("utf-8"))`); CRC recalculado sobre o payload bate com os 4 ultimos chars.
- [ ] `resolve_pix_recipient(lease)` resolve cidade por `Landlord.city` → `FinancialSettings.default_city` → `_DEFAULT_CITY`, e o viewset nao tem mais `city="Sao Paulo"` hardcoded.
- [ ] `POST /api/tenant/payments/pix/` com owner de nome acentuado devolve 200 (regressao do 500).
- [ ] `send_whatsapp_message` passa `content_variables` como string JSON (`json.dumps`), verificado pelo mock da fronteira Twilio.
- [ ] `FinancialSettings.default_city` existe + migration aplicada; sem RLS RunSQL (tabela ja existia).
- [ ] Gate de verificacao passa (escopado) com zero erros e zero warnings.

## Gate de verificação

Escopado nos arquivos editados + regressao dirigida (a suite cheia tem flakiness pre-existente de xdist/Redis — nao e bloqueio):

```bash
ruff check core/services/pix_service.py core/services/whatsapp_service.py core/viewsets/tenant_views.py core/models.py
ruff format --check core/services/pix_service.py core/services/whatsapp_service.py core/viewsets/tenant_views.py core/models.py
mypy core/services/pix_service.py core/services/whatsapp_service.py core/viewsets/tenant_views.py
pyright core/services/pix_service.py core/services/whatsapp_service.py core/viewsets/tenant_views.py
python -m pytest tests/unit/test_pix_service.py tests/unit/test_pix_recipient.py tests/unit/test_whatsapp_service.py tests/integration/test_tenant_api.py -p no:cacheprovider
```

Frontend: N/A (sem mudanca em `frontend/`). Validacao manual recomendada (fora do CI): um envio real no sandbox Twilio confirmando que as variaveis chegam substituidas — a fronteira e mockada nos testes.

## Handoff

- Commit sugerido:
  ```
  fix(tenant): sanitize PIX EMV to ASCII + bytes-length TLV; send Twilio content_variables as JSON

  - pix_service: NFKD/ASCII-upper sanitization for merchant name/city (no more
    UnicodeEncodeError 500 on accented names); TLV length in bytes per BCB spec
  - resolve_pix_recipient service: configurable city (Landlord/FinancialSettings),
    removes hardcoded "Sao Paulo" and inline recipient logic from the viewset
  - whatsapp_service: content_variables=json.dumps(...) so template vars substitute
  - FinancialSettings.default_city field + migration

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```
- Acoes de ops (manual, pos-merge): setar `Landlord.city` (ou `FinancialSettings.default_city`) = "Porto Alegre" em prod via admin; validar um OTP WhatsApp real no sandbox Twilio.
- O proximo plano que tocar o fluxo PIX mobile (campo `payload` → `pix_copy_paste` em `mobile/app/(tenant)/payments/pix.tsx`) assume que o backend ja devolve `pix_copy_paste`/`qr_data` validos (sanitizados) — este plano nao altera o nome dos campos de retorno.
- Atualizar MEMORY: adicionar nota "PIX EMV sanitizado + Twilio content_variables JSON (branch fix/pix-emv-and-whatsapp)".
