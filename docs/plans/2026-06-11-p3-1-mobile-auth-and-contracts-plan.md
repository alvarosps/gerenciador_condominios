# Plano P3.1 — Mobile: auth (token no body) + correção de todos os contratos de API

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P3 (Mobile) · **Branch sugerida:** `fix/mobile-api-realignment` · **Depende de:** nenhum (idealmente após P1.2 papel/permissões, mas pode ir em paralelo). As 4 telas do financeiro LEGADO (`mobile/app/(admin)/financial/*`, `use-admin-financial.ts`) NÃO são corrigidas aqui — são REMOVIDAS no plano **P3.2**.

## Objetivo

O app Expo (`mobile/`) é consumidor vivo de `/api/`, mas o cliente de auth foi escrito em 30/03 e o backend migrou para JWT em cookie HttpOnly em 06/04 (commit f7968ab): `CookieTokenObtainPairView`/`CookieTokenRefreshView` zeram o body, então o login admin do app não recebe `{access,refresh}` e o refresh nunca recebe o novo `access` (sessão morre a cada 60min). Além disso, ~10 telas foram escritas contra shapes de API que nunca existiram (PIX, reajuste, marcar-pago, criar-locação, atrasados, notificações read-all, download de contrato, generate_contract). Este plano realinha o contrato mobile↔backend nos **dois lados**: backend devolve tokens no body para clientes não-browser e expõe `tenant_name`/`apartment_number` no comprovante admin; o app corrige auth, shapes, dual-pattern, paginação e checagem de status no download — sem tocar no módulo financeiro legado além do estritamente necessário.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | Login admin quebrado — backend não devolve tokens no body | `mobile/app/login.tsx:43-55` + `core/viewsets/auth_views_cookie.py:80-97` | Novo `/api/auth/token/mobile/` (ou flag header) devolve `{access,refresh,user}`; login usa esse endpoint |
| ALTO | Refresh quebrado — `CookieTokenRefreshView` faz `response.data={}` | `mobile/lib/api/client.ts:64-88` + `auth_views_cookie.py:100-126` | Quando `refresh` vem no body (não-browser) devolver `{access,refresh}` no body |
| ALTO | Logout não revoga refresh (lê só COOKIES) | `mobile/store/auth-store.ts:43-54` + `auth_views_cookie.py:129-141` | `cookie_logout` aceita `refresh` no body como fallback; `clearAuth` chama logout antes de limpar |
| ALTO | PIX lê `payload` inexistente (backend = `pix_copy_paste`/`qr_data`) | `mobile/app/(tenant)/payments/pix.tsx:35,80,124` + `mobile/lib/schemas/tenant.ts:61-67` | Trocar `payload`→`pix_copy_paste` (copiar/pix_code) e `qr_data` (QR); `.parse()` na resposta |
| ALTO | Criar locação envia `apartment`/`responsible_tenant_id` (sem dual pattern) → 400 | `mobile/lib/api/hooks/use-admin-properties.ts:65-79` | Enviar `apartment_id` + `tenant_ids:[responsible_tenant_id]`; exibir erros de campo do DRF |
| ALTO | Reajuste trata `{alerts:[...]}` como array → crash | `mobile/app/(admin)/actions/rent-adjustment.tsx` + `use-admin-dashboard.ts:46-56` | Ler `response.data.alerts`; tipar campos reais (`tenant`/`apartment`/`eligible_date`/`days_until`/`ipca_percentage`) |
| ALTO | Mark-paid trata `lease.apartment` (objeto aninhado) como number → crash | `mobile/app/(admin)/actions/mark-paid.tsx:81` + `mobile/lib/schemas/admin.ts:20-32` | Tipar `apartment` como objeto `{id,number}`; renderizar `.number`, comparar `.id` |
| ALTO | Listas truncadas em 20 (sem `page_size`) — admin não marca ~17 locações | `use-admin-properties.ts:12-63`, `use-tenant.ts`, `use-admin-actions.ts:58-69` | `page_size` alto explícito nos hooks de lista (100; leases/apartments/proofs/payments) |
| MÉDIO | Card "Atrasados" shape divergente (sempre 0) | `use-admin-dashboard.ts:20-34` | Tipar `total_late_leases`/`total_late_fees`/`late_leases[]` com `late_days`/`late_fee`/`building_number` |
| MÉDIO | read-all admin chama rota inexistente `/notifications/read-all/` → 404 | `use-admin-notifications.ts:46-48` | Trocar para `/admin/notifications/read-all/` |
| MÉDIO | Download de contrato não checa status (salva JSON de erro como pdf) | `mobile/app/(tenant)/contract.tsx:17-44` | Checar `downloadResult.status===200`, apagar arquivo e mostrar erro caso contrário |
| MÉDIO | `generate_contract` tipado `{contract_url}` (real `{pdf_path}`/202 `{task_id}`) | `use-admin-properties.ts:88-105` | Tipar união 200/202; no 202 fazer polling em `/api/tasks/{id}/status/` |
| MÉDIO | Aprovação de comprovante às cegas (sem arquivo, sem `tenant_name`/`apartment_number`) | `mobile/app/(admin)/actions/proofs.tsx:38-44` + `core/viewsets/proof_views.py:32-53` | Backend: serializer admin com `tenant_name`/`apartment_number`; mobile: exibir o `file` |

## Abordagem técnica

Ordem recomendada: **backend primeiro** (auth + proof serializer + testes), depois **mobile** (auth client, depois shapes), pois o mobile depende do novo endpoint de token e dos campos do comprovante.

### 1. Backend — endpoint de token para clientes não-browser (`core/viewsets/auth_views_cookie.py`)

Hoje `CookieTokenObtainPairView.post` (linhas 80-97) chama `super().post()`, seta cookies via `_set_auth_cookies`, e **substitui** `response.data` por `{"user": {...}}` — descartando `access`/`refresh`. `CookieTokenRefreshView.post` (100-126) faz `response.data = {}`. `cookie_logout` (129-141) lê `refresh_token` só de `request.COOKIES`.

Decisão (KISS, sem header-sniffing frágil): **expor um par de endpoints dedicados a clientes não-browser** que reaproveitam os serializers do simplejwt e devolvem os tokens no body, mantendo os endpoints cookie intactos para o web.

- Criar `class MobileTokenObtainPairView(TokenObtainPairView)`: `post()` chama `super().post()`; se 200, anexa o bloco `user` (resolvendo `user` via `AccessToken(response.data["access"])["user_id"]`, igual ao padrão das linhas 86-95) e **mantém** `access`/`refresh` no body. **Não** seta cookies (cliente mobile não usa cookies). Extrair a montagem do dict `user` para um helper `_user_payload(user) -> dict` reutilizado pela cookie view e pela mobile view (DRY — hoje está inline em 88-95).
- Ajustar `CookieTokenRefreshView.post` (100-126): quando `refresh` vier **no body** (ramo `else`, sem cookie — i.e. `"refresh" in request.data`), em vez de `response.data = {}`, **devolver** `{"access": access, "refresh": new_refresh}` no body (sem setar cookies). Quando vier do cookie (ramo das linhas 102-118), manter o comportamento atual (`response.data = {}` + cookies). Isso evita um terceiro endpoint para refresh.
- Ajustar `cookie_logout` (129-141): ler `refresh_token = request.COOKIES.get("refresh_token") or request.data.get("refresh")`. O resto (blacklist + `_clear_auth_cookies`) é idêntico. Cliente mobile passa a poder blacklistar.
- Registrar a rota: em `condominios_manager/urls.py` adicionar `path("api/auth/token/mobile/", ThrottledMobileTokenObtainPairView.as_view(), name="token_obtain_mobile")` com a mesma `AuthRateThrottle` das views existentes (linhas 42-47). O refresh continua em `api/auth/token/refresh/` (mesmo endpoint, agora bifurca por presença de `refresh` no body).

**Constraint de design:** lógica de auth fica nas views de auth (já é a camada correta para JWT); não criar service novo para isso — seria YAGNI.

### 2. Backend — comprovante admin com `tenant_name`/`apartment_number` (`core/viewsets/proof_views.py` + `core/serializers.py`)

`AdminProofViewSet.list` (32-53) já faz `select_related("lease__apartment__building","lease__responsible_tenant")` — os joins existem, os dados são carregados e descartados. `PaymentProofSerializer` (serializers.py:1248-1271) não expõe `tenant_name`/`apartment_number`.

- Criar `class AdminPaymentProofSerializer(serializers.ModelSerializer)` em `core/serializers.py` (ou estender via SerializerMethodFields num serializer dedicado — preferir serializer dedicado para o portal admin, sem inflar o serializer do inquilino): campos `id, lease, reference_month, file, pix_code, status, created_at, tenant_name, apartment_number`. `tenant_name = serializers.CharField(source="lease.responsible_tenant.name", read_only=True)` e `apartment_number = serializers.CharField(source="lease.apartment.number", read_only=True)` — usa os joins já presentes, sem N+1.
- `AdminProofViewSet.list` (linha 52) passa a usar `AdminPaymentProofSerializer`. `review` (linha 100) pode continuar com `PaymentProofSerializer` (resposta da ação, não precisa dos nomes).

### 3. Mobile — auth client (`mobile/app/login.tsx`, `mobile/lib/api/client.ts`, `mobile/store/auth-store.ts`)

- `login.tsx` (`handleAdminLogin`, 36-61): trocar `POST /auth/token/` por `POST /auth/token/mobile/`; a resposta agora traz `{access, refresh, user:{id,first_name,last_name,is_staff}}`. Usar `res.data.user` (ou manter o segundo GET `/auth/me/`, mas o `user` no body elimina o round-trip). Manter `setAuth(user, access, refresh)`.
- `client.ts` interceptor de refresh (64-88): o backend agora devolve `{access, refresh}` no body. Ler `response.data.access` (já lê) **e** persistir o novo `refresh` quando presente (rotação): `if (response.data.refresh) await setRefreshToken(response.data.refresh)`. Tratar resposta **sem** `access` como falha explícita (não chamar `setAccessToken(undefined)` — hoje isso lança no expo-secure-store): `if (!newAccessToken) throw new Error("Refresh sem access")`.
- `auth-store.ts` `clearAuth` (43-54): antes de limpar a SecureStore, chamar `POST /auth/logout/` com `{refresh}` (lido da SecureStore) para blacklistar — dentro de try/catch (logout best-effort, não bloquear a limpeza local). Importante: chamar `unregisterPushToken()` **antes** de invalidar o access (a ordem atual já faz isso). Não chamar request autenticado depois de limpar tokens.

### 4. Mobile — PIX (`mobile/lib/schemas/tenant.ts`, `mobile/app/(tenant)/payments/pix.tsx`)

Backend `generate_pix_payload` (pix_service.py:85-86) retorna `pix_copy_paste` e `qr_data` (ambos = EMV), além de `pix_key`/`pix_key_type`/`amount`/`merchant_name`.

- `PixPayloadSchema` (tenant.ts:61-67): substituir `payload: z.string()` por `pix_copy_paste: z.string()` e `qr_data: z.string()`.
- `pix.tsx`: `handleCopyPix` (35) usa `pixPayload.pix_copy_paste`; `<QRCode value={pixPayload.qr_data}/>` (124); `submitProof` (80) envia `pix_code: pixPayload?.pix_copy_paste`.
- `useGeneratePix` (use-tenant-pix.ts): validar `PixPayloadSchema.parse(response.data)` para drift futuro falhar ruidosamente.

### 5. Mobile — dual pattern criar locação + erros de campo (`use-admin-properties.ts`)

`LeaseSerializer` exige `apartment_id` (PrimaryKeyRelatedField write_only, source='apartment') e `tenant_ids` (many) — serializers.py:378-386.

- `CreateLeaseInput` (65-72): trocar `apartment: number` + `responsible_tenant_id` por `apartment_id: number`, `responsible_tenant_id: number`, `tenant_ids: number[]`. No `useCreateLease` montar o body `{apartment_id, responsible_tenant_id, tenant_ids:[responsible_tenant_id], start_date, validity_months, rental_value, number_of_tenants}` (espelha o frontend web). Atualizar `new-lease.tsx` para passar `apartment_id`.
- Exibir erros de campo: no `onError` da tela, extrair `error.response.data` (DRF `{field:[msgs]}`) e mostrar no `Alert` — reutilizar o padrão já presente em `mark-paid.tsx:46-53` (extrair um helper `mobile/lib/api/error-message.ts` para DRY, usado por mark-paid, new-lease e rent-adjustment).

### 6. Mobile — reajuste shape (`use-admin-dashboard.ts`, `rent-adjustment.tsx`, `mobile/lib/schemas/admin.ts`)

Backend `rent_adjustment_alerts` retorna `{"alerts":[...], ipca_latest_month, fallback_percentage, ipca_percentage}` (rent_adjustment_service.py:298); cada alerta tem `lease_id`/`tenant`/`apartment`/`eligible_date`/`days_until`/`ipca_percentage` — **não** há `months_since_adjustment`/`tenant_name`/`apartment_number`.

- `useRentAdjustmentAlerts` (46-56): retornar `response.data.alerts` (não `response.data`). Tipar com um `RentAdjustmentAlertSchema` corrigido aos campos reais. Verificar a fonte exata dos campos lendo `rent_adjustment_service.py` (montagem do dict de alerta) antes de fixar os nomes.
- `rent-adjustment.tsx`: usar `alert.tenant`/`alert.apartment`/`alert.days_until` na renderização (linha 84) em vez de `tenant_name`/`apartment_number`/`months_since_adjustment`. `ipca_percentage` pode pré-preencher o campo de percentual.

### 7. Mobile — mark-paid apartment objeto + filtro de lista (`mobile/lib/schemas/admin.ts`, `mark-paid.tsx`, `properties/[id].tsx`)

`LeaseSerializer.apartment = ApartmentSerializer(read_only=True)` (serializers.py:377) — no read é objeto aninhado. O endpoint `/leases/` serializa com `LeaseSerializer` completo.

- `LeaseSimpleSchema` (admin.ts:20-32): trocar `apartment: z.number()` por `apartment: z.object({ id: z.number(), number: z.string() })` (campos mínimos usados; o serializer entrega mais, mas Zod ignora extras por default). 
- `mark-paid.tsx:81`: renderizar `Apto {lease.apartment.number}`. `properties/[id].tsx`: comparar `l.apartment.id === apartmentId`. O filtro `building_id` em `/leases/` não é suportado pelo `LeaseViewSet` (só `apartment_id`/`responsible_tenant_id`/`is_active`); filtrar client-side pelos apartamentos do prédio (ou remover o filtro inválido e filtrar em memória).

### 8. Mobile — atrasados shape (`use-admin-dashboard.ts`, `mobile/lib/schemas/admin.ts`)

Backend `late_payment_summary` (views.py:680-707 / dashboard_service.py:298-424) retorna `{total_late_leases, total_late_fees, average_late_days, late_leases:[{lease_id, apartment_number, building_number, tenant_name, rental_value, due_day, late_days, late_fee}]}`.

- `LatePaymentSummary` (20-24) e `LatePaymentItemSchema` (admin.ts:42-49): realinhar para essas chaves. No dashboard, ler `total_late_leases` e `total_late_fees`.

### 9. Mobile — read-all url (`use-admin-notifications.ts:46-48`)

Trocar `POST /notifications/read-all/` por `POST /admin/notifications/read-all/` (action registrada em `admin/notifications` com `url_path="read-all"`, notification_views.py:55; resposta `{marked_read:count}`).

### 10. Mobile — download de contrato (`mobile/app/(tenant)/contract.tsx:17-44`)

`FileSystem.downloadAsync` não rejeita em status de erro. Após o download: `if (downloadResult.status !== 200) { await FileSystem.deleteAsync(downloadResult.uri,{idempotent:true}); Alert.alert("Erro", ...); return; }` antes de compartilhar. Extrair `API_BASE_URL` (duplicado aqui e em client.ts:3) para `mobile/lib/api/config.ts` (DRY).

### 11. Mobile — generate_contract 202/polling (`use-admin-properties.ts:88-105`)

Backend retorna 200 `{pdf_path, message}` (eager) **ou** 202 `{task_id, status:"processing"}` (async — views.py:386-394). `GenerateContractResponse` deve ser união. No mutationFn: se status 202, fazer polling em `/api/tasks/{task_id}/status/` (views.py:869) até `status` final, e só então resolver sucesso/erro. Manter compatível com o eager (200 resolve direto).

### 12. Mobile — paginação alta nos hooks de lista

Passar `params:{ page_size: 100 }` (preferência declarada do produto) em: `useBuildings`, `useApartments`, `useLeases`, `useTenantSearch` (use-admin-properties.ts:12-63), `useAdminProofs` (use-admin-actions.ts:58-69), `useTenantPayments`, `useTenantAdjustments` (use-tenant.ts). `CustomPageNumberPagination` aceita `page_size` até 500; 100 cobre prod (~37 locações).

## Arquivos a criar / modificar

**Backend**
- `core/viewsets/auth_views_cookie.py` — novo `MobileTokenObtainPairView`; helper `_user_payload`; `CookieTokenRefreshView.post` devolve tokens no body quando `refresh` vem no body; `cookie_logout` aceita `refresh` no body.
- `condominios_manager/urls.py` — `ThrottledMobileTokenObtainPairView` + rota `api/auth/token/mobile/`.
- `core/serializers.py` — novo `AdminPaymentProofSerializer` (`tenant_name`/`apartment_number`).
- `core/viewsets/proof_views.py` — `list` usa `AdminPaymentProofSerializer`.
- `tests/integration/test_auth_views_cookie.py` (ou arquivo existente de auth) — testes do token mobile / refresh body / logout body.
- `tests/integration/test_proof_views.py` — teste do novo serializer admin.

**Mobile**
- `mobile/app/login.tsx` — admin usa `/auth/token/mobile/`.
- `mobile/lib/api/client.ts` — refresh lê/grava `access`+`refresh` do body; trata ausência de `access`.
- `mobile/store/auth-store.ts` — `clearAuth` chama `POST /auth/logout/` com `{refresh}`.
- `mobile/lib/api/config.ts` — **novo**: `API_BASE_URL` único.
- `mobile/lib/api/error-message.ts` — **novo**: extrai mensagens de erro de campo do DRF.
- `mobile/lib/schemas/tenant.ts` — `PixPayloadSchema` (`pix_copy_paste`/`qr_data`).
- `mobile/lib/schemas/admin.ts` — `LeaseSimpleSchema.apartment` objeto; `LatePaymentItemSchema`; `RentAdjustmentAlertSchema`.
- `mobile/lib/api/hooks/use-admin-properties.ts` — dual pattern create; `page_size`; generate_contract união+polling.
- `mobile/lib/api/hooks/use-admin-dashboard.ts` — late_payment shape; `useRentAdjustmentAlerts` lê `.alerts`.
- `mobile/lib/api/hooks/use-admin-notifications.ts` — url read-all.
- `mobile/lib/api/hooks/use-admin-actions.ts` — `useAdminProofs` `page_size`.
- `mobile/lib/api/hooks/use-tenant.ts` — `page_size` em payments/adjustments.
- `mobile/lib/api/hooks/use-tenant-pix.ts` — `.parse()`.
- `mobile/app/(tenant)/payments/pix.tsx` — campos PIX corretos.
- `mobile/app/(admin)/actions/mark-paid.tsx` — `lease.apartment.number`.
- `mobile/app/(admin)/actions/rent-adjustment.tsx` — campos reais do alerta.
- `mobile/app/(admin)/actions/proofs.tsx` — exibir `file`; usar `tenant_name`/`apartment_number`.
- `mobile/app/(admin)/properties/[id].tsx` — `apartment.id`; filtro client-side.
- `mobile/app/(admin)/properties/new-lease.tsx` — `apartment_id`/`tenant_ids`.
- `mobile/app/(tenant)/contract.tsx` — checar status; usar `API_BASE_URL` de config.

## TDD — cenários de teste

**Backend (pytest, mock só na fronteira: nenhum — usa client real DRF + DB)**
- `test_mobile_token_returns_access_refresh_and_user_in_body` — POST `/api/auth/token/mobile/` com credenciais válidas retorna 200 com `access`, `refresh` e `user.is_staff` no body (regressão do login admin quebrado).
- `test_mobile_token_invalid_credentials_returns_401` — credenciais erradas → 401, sem tokens.
- `test_cookie_token_obtain_still_strips_body` — POST `/api/auth/token/` (web) continua devolvendo só `{user}` + cookies (não regredir o web).
- `test_refresh_with_body_returns_new_access_in_body` — POST `/api/auth/token/refresh/` com `{refresh}` no body retorna `access` (e `refresh` se rotação) no body — **não** `{}` (regressão do refresh quebrado).
- `test_refresh_with_cookie_keeps_empty_body` — refresh via cookie continua `response.data == {}` + cookies (web intacto).
- `test_logout_blacklists_refresh_from_body` — POST `/api/auth/logout/` com `{refresh}` no body blacklista o token (refresh subsequente → 401).
- `test_logout_still_blacklists_refresh_from_cookie` — fluxo web continua funcionando.
- `test_admin_proof_list_includes_tenant_name_and_apartment_number` — GET `/api/admin/proofs/?status=pending` traz `tenant_name` e `apartment_number` corretos; sem N+1 extra (assertNumQueries em torno do baseline com select_related).

**Mobile (vitest + MSW na fronteira HTTP)** — adicionar infra de teste mínima (ver Constraints; gate atual do mobile não tem vitest):
- `client.refresh.updates-access-and-refresh` — 401 → refresh retorna `{access,refresh}` no body → access atualizado, refresh persistido, request original re-tentado com novo Bearer.
- `client.refresh.missing-access-throws-not-undefined-set` — refresh sem `access` → não chama `setAccessToken(undefined)`; chama `clearAuth` (regressão do logout horário).
- `login.admin.uses-mobile-token-endpoint` — admin login chama `/auth/token/mobile/` e armazena tokens do body.
- `pix.maps-copy-paste-and-qr` — resposta `{pix_copy_paste, qr_data}` → copiar usa `pix_copy_paste`, QR usa `qr_data`; `.parse()` rejeita resposta com `payload`.
- `create-lease.sends-dual-pattern` — POST `/leases/` envia `apartment_id` + `tenant_ids`; 400 do DRF exibe erro de campo.
- `rent-adjustment.reads-alerts-array` — resposta `{alerts:[...]}` → hook devolve o array; tela renderiza `tenant`/`apartment` (regressão do crash `alerts.map`).
- `mark-paid.renders-apartment-number` — `lease.apartment` objeto → renderiza `.number`, não crash de "Objects are not valid as a React child".
- `late-payments.reads-real-shape` — `{total_late_leases,total_late_fees,late_leases}` → card mostra valores reais (regressão do "sempre 0").
- `notifications.read-all-url` — mutation faz POST em `/admin/notifications/read-all/` (regressão do 404).
- `contract-download.error-status-deletes-and-alerts` — `downloadAsync` com status 404 → arquivo apagado, Alert de erro, não compartilha (regressão do JSON-como-pdf).
- `generate-contract.handles-202-polling` — 202 `{task_id}` → faz polling em `/api/tasks/{id}/status/` e só então confirma; 200 `{pdf_path}` resolve direto.
- `list-hooks.send-page-size` — hooks de lista enviam `page_size=100`.

## Migrations / dados

N/A — nenhuma mudança de schema. Só código (views/serializers/hooks/screens). Sem RLS, sem backup necessário. O novo `AdminPaymentProofSerializer` apenas lê campos já existentes via joins já presentes.

## Constraints (o que NÃO fazer)

- **NÃO** corrigir as 4 telas do financeiro legado (`mobile/app/(admin)/financial/*`, `use-admin-financial.ts`, `/financial-dashboard/*`, `/daily-control/*`) — são REMOVIDAS em P3.2. Não tocar no módulo `core` financeiro pessoal além do necessário.
- **NÃO** refatorar `CookieTokenObtainPairView`/`CookieTokenRefreshView` para o fluxo web — o web depende do body zerado + cookies; apenas **adicionar** o ramo body e o endpoint mobile sem regredir o web.
- **NÃO** introduzir header-sniffing de user-agent para decidir body vs cookie — usar endpoint dedicado (`/token/mobile/`) e presença de `refresh` no body (explícito, testável).
- **NÃO** usar `# noqa`/`# type: ignore`/`eslint-disable`/`@ts-ignore`/`@ts-expect-error`. Sem `from __future__ import annotations`. Decimal nunca vira float; valores monetários permanecem string vinda da API.
- **NÃO** quebrar o login de inquilino via WhatsApp (que já funciona e devolve `{access,refresh}` no body) nem o portal do inquilino.
- DRY: `API_BASE_URL` e o extrator de erro DRF em módulos únicos; não duplicar.

## Critérios de aceite (binários)

- [ ] POST `/api/auth/token/mobile/` retorna `{access, refresh, user}` no body; `/api/auth/token/` (web) continua `{user}`+cookies.
- [ ] POST `/api/auth/token/refresh/` com `{refresh}` no body retorna `access` (e `refresh` se rotação) no body; via cookie continua `{}`+cookies.
- [ ] POST `/api/auth/logout/` com `{refresh}` no body blacklista o token; via cookie continua funcionando.
- [ ] GET `/api/admin/proofs/` traz `tenant_name` e `apartment_number`.
- [ ] Mobile: login admin entra com sucesso; sessão sobrevive ao refresh (sem logout a cada 60min).
- [ ] Mobile PIX: QR válido e "copiar código" funcionam (`qr_data`/`pix_copy_paste`).
- [ ] Mobile: criar locação envia `apartment_id`+`tenant_ids`; erro 400 mostra mensagem de campo.
- [ ] Mobile: telas reajuste e marcar-pago renderizam sem crash; card "Atrasados" mostra valores reais.
- [ ] Mobile: "marcar todas notificações lidas" não retorna 404.
- [ ] Mobile: download de contrato com erro não compartilha pdf corrompido.
- [ ] Mobile: hooks de lista trazem >20 itens (page_size 100).
- [ ] Backend gate verde (ruff/mypy/pyright nos arquivos editados + pytest dos testes novos). Mobile `type-check` verde + vitest novos verdes.

## Gate de verificação

```bash
# Backend — escopado nos arquivos editados + regressão dirigida de auth/proof
ruff check core/viewsets/auth_views_cookie.py core/viewsets/proof_views.py core/serializers.py condominios_manager/urls.py
ruff format --check core/viewsets/auth_views_cookie.py core/viewsets/proof_views.py core/serializers.py condominios_manager/urls.py
mypy core/ && pyright
python -m pytest tests/integration/test_auth_views_cookie.py tests/integration/test_proof_views.py -p no:randomly
# (suite cheia tem flakiness pré-existente de xdist/Redis — não bloqueante)

# Mobile
cd mobile && npx tsc --noEmit
# após adicionar vitest+MSW (ver Constraints): npm run test:unit
```

## Handoff

Commit sugerido:

```
fix(mobile): realign auth + API contracts with cookie-JWT backend

- backend: /api/auth/token/mobile/ + refresh-in-body + logout-in-body for
  non-browser clients; AdminPaymentProofSerializer (tenant_name/apartment_number)
- mobile: fix admin login/refresh/logout, PIX fields, lease dual-pattern,
  rent-adjustment .alerts, mark-paid apartment object, late-payment shape,
  read-all url, contract download status check, generate_contract 202 polling,
  page_size on list hooks

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar `MEMORY.md` (`project_mobile_app_consumer.md`): mobile realinhado ao backend cookie-JWT; endpoint `/api/auth/token/mobile/` é o caminho do app; refresh bifurca por presença de `refresh` no body. O **próximo plano (P3.2)** assume que o auth/refresh do mobile está funcional e REMOVE as 4 telas do financeiro legado (`mobile/app/(admin)/financial/*` + `use-admin-financial.ts` + rota no `_layout`), além de (opcionalmente) adicionar ESLint/Prettier/vitest ao gate do mobile e `.parse()` em todos os hooks.
