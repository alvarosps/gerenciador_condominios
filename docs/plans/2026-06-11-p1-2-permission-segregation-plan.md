# Plano P1.2 — Segregação inquilino×admin + travar endpoints financeiros a is_staff

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P1 · **Branch sugerida:** `fix/permission-segregation` · **Depende de:** P0.1

## Objetivo

Hoje um inquilino autenticado via OTP (WhatsApp) recebe `is_staff=False` mas, no backend, lê toda a PII de outros inquilinos (`GET /api/tenants`), todas as locações, apartamentos e TODO o financeiro (legado `FinancialReadOnly` + o app novo `finances/`); no frontend, navega por URL direta para `/`, `/buildings`, `/finances/*` porque o `middleware.ts` só checa presença de cookie, não papel. Este plano fecha os dois lados: no backend troca as permissões que liberam leitura a qualquer autenticado por `IsAdminUser` onde a leitura por inquilino é indevida e escopa `tenants`/`leases` ao próprio inquilino quando não-staff; no frontend introduz um claim de papel (cookie `role`) acessível ao middleware, bloqueia rotas do dashboard para tenants (redirect `/tenant`) e adiciona guard no `MainLayout`. O portal do inquilino (`/api/tenant/*`, já protegido por `IsTenantUser`) permanece intacto.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| ALTO | `ReadOnlyForNonAdmin` libera leitura de Building/Apartment/Tenant a qualquer autenticado | `core/views.py:77,107,129,194` | Buildings/Apartments/Furniture viram `IsAuthenticatedAndActive`+staff-write via `ReadOnlyForNonAdmin` mantido; Tenant passa a escopar queryset por inquilino |
| ALTO | `CanModifyLease` deixa qualquer autenticado ler todas as leases | `core/views.py:275` | `LeaseViewSet.get_queryset` escopa por `responsible_tenant.user` quando não-staff |
| ALTO | `FinancialReadOnly` libera leitura de TODO o financeiro a inquilino (legado E `finances/`) | `core/permissions.py:107`; `finances/viewsets/*`; `core/viewsets/financial_views.py`, `financial_dashboard_views.py` | Trocar `FinancialReadOnly` por `IsAdminUser` em todos os viewsets de `finances/` e nos financeiros do core |
| ALTO (FE) | `middleware.ts` só checa cookie `is_authenticated`, não papel; sem guard no `MainLayout` | `frontend/middleware.ts:25-49`; `frontend/components/layouts/main-layout.tsx` | Cookie `role` setado no login; middleware redireciona tenant→`/tenant`; guard de papel no `MainLayout` |
| MÉDIO | Duas classes `IsAdminUser` (DRF vs `core.permissions`) com semânticas diferentes | `core/viewsets/month_advance_views.py:5`; `core/viewsets/auth_views.py:16` (DRF) vs `core/auth.py`/`core/permissions.py:32` | Unificar todos os consumidores para `core.permissions.IsAdminUser` |

> Observação de escopo: o módulo financeiro pessoal do core (`financial_views.py`, `financial_dashboard_views.py`) é DEPRECATED. Mesmo assim, trocar `FinancialReadOnly→IsAdminUser` ali é um swap de uma classe por outra (sem refatoração de lógica), e é o que fecha a brecha de leitura por inquilino. Manter a mudança mínima: apenas o `permission_classes`.

## Abordagem técnica

Ordem de execução (backend primeiro, depois frontend; TDD em cada passo):

### 1. Backend — semântica única de `IsAdminUser` (achado MÉDIO)

`core/permissions.IsAdminUser` (linhas 32-44) já cobre `is_staff OR is_superuser`. A `rest_framework.permissions.IsAdminUser` cobre só `is_staff`. Para superusers que não sejam staff, as semânticas divergem. Unificar:
- `core/viewsets/month_advance_views.py:5` — remover `from rest_framework.permissions import IsAdminUser`, importar `from core.permissions import IsAdminUser`.
- `core/viewsets/auth_views.py:16` — o import DRF traz `AllowAny, IsAdminUser, IsAuthenticated`; manter `AllowAny, IsAuthenticated` do DRF e importar `IsAdminUser` de `core.permissions` (usado em `oauth_status`, linha 185). Não misturar os dois nomes no mesmo módulo.
- Verificar com grep que NENHUM outro módulo importa `IsAdminUser` de `rest_framework.permissions`. `core/viewsets/auth_views.py` (whatsapp, linha 28) e `landlord_views`, `proof_views`, `rule_views`, `notification_views`, `user_admin_views`, `template_views`, `financial_dashboard_views` já usam `core.permissions.IsAdminUser` — confirmar e não tocar.

### 2. Backend — travar TODO o financeiro a `is_staff` (achado ALTO financeiro)

Trocar `FinancialReadOnly` por `core.permissions.IsAdminUser` (leitura E escrita só staff) em:
- `finances/viewsets/crud_views.py`: `CategoryViewSet` (98), `BillingAccountViewSet` (115), `BillSkipViewSet` (138), `PaymentViewSet` (155), `BillViewSet` (285), `ReserveViewSet` (570), `ReserveMovementViewSet` (627), `IncomeEntryViewSet` (650), `CondoMonthCloseViewSet` (676). Substituir o `from core.permissions import FinancialReadOnly` por `from core.permissions import IsAdminUser` e cada `permission_classes = [FinancialReadOnly]` por `[IsAdminUser]`.
- `finances/viewsets/dashboard_views.py`: linhas 199, 351 (`FinanceDashboardViewSet` e o segundo viewset de dashboard).
- `finances/viewsets/installment_payroll_views.py`: linhas 34, 118, 139.
- Core financeiro legado: `core/viewsets/financial_views.py` (todas as ~14 ocorrências de `FinancialReadOnly`) e `core/viewsets/financial_dashboard_views.py:27` (as linhas 144/274 já são `IsAdminUser`).

Após a troca, remover `FinancialReadOnly` de `core/permissions.py` SOMENTE se grep confirmar zero consumidores restantes (incluindo `mobile/` — ver Constraints). Se algum consumidor legítimo permanecer (ex.: leitura por inquilino que se queira manter), NÃO remover a classe; apenas deixar de usá-la nos viewsets administrativos. Atualizar `PERMISSION_CLASSES["financial_read_only"]` (permissions.py:248) coerentemente: se a classe for removida, remover a entrada do dict e procurar usos de `get_permission_classes('financial_read_only')`.

### 3. Backend — escopar `tenants` e `leases` ao próprio inquilino (achados ALTO)

`TenantViewSet` (`core/views.py:175`) e `LeaseViewSet` (`core/views.py:254`) hoje retornam TUDO para qualquer autenticado. Escopar por papel no `get_queryset`:

- `TenantViewSet.get_queryset` (linha 196): no início, se `self.request.user` autenticado e `not is_staff`, restringir ao próprio tenant. O vínculo é `Tenant.user` (FK reverso `request.user.tenant_profile`, usado em `IsTenantUser`/`_get_tenant`). Implementar:
  ```
  user = self.request.user
  if user.is_authenticated and not user.is_staff:
      queryset = queryset.filter(user=user)
  ```
  aplicado ANTES dos filtros de query-param (que continuam válidos sobre o queryset já escopado). Resultado: inquilino vê só o próprio registro; staff vê todos.
- `LeaseViewSet.get_queryset` (linha 311): após o `select_related` e ANTES dos filtros de list, aplicar:
  ```
  user = self.request.user
  if user.is_authenticated and not user.is_staff:
      queryset = queryset.filter(responsible_tenant__user=user)
  ```
  Isso preserva a permissão `CanModifyLease` (leitura por qualquer autenticado, escrita só staff) mas agora o inquilino só ENXERGA as próprias leases. As actions `calculate_late_fee` (`IsTenantOrAdmin`) e `generate_contract` (`CanGenerateContract`) continuam com `get_object()` operando sobre o queryset escopado — um inquilino não consegue mais agir sobre lease alheia (defesa em profundidade junto com `has_object_permission`).

> Decisão de design: escopar via `get_queryset` (não 403) para que o inquilino veja a própria lease/o próprio cadastro sem vazar a existência de outros. `ApartmentViewSet`/`BuildingViewSet`/`FurnitureViewSet` permanecem `ReadOnlyForNonAdmin` (dados de referência que o inquilino pode legitimamente ler de forma agregada; o vazamento de PII está em Tenant/Lease/financeiro, que são os que travamos). Se P0.1 ou revisão exigir travar também apartments/buildings a staff, fazer no mesmo padrão de swap — fora do escopo confirmado aqui.

### 4. Frontend — claim de papel acessível ao middleware (achado ALTO FE)

O middleware roda no Edge e só lê cookies (não tem acesso ao JWT HttpOnly nem ao zustand). Precisa de um cookie NÃO-HttpOnly `role` com `staff|tenant`.

Backend — setar `role` junto de `is_authenticated`:
- `core/viewsets/auth_views_cookie.py`: `_set_auth_cookies` (linha 41) NÃO conhece o user. Adicionar parâmetro `role: str` e setar um cookie `role` (httponly=False, mesmo `secure`/`samesite`/`max_age`/`path` do `is_authenticated`, linhas 63-71). `_clear_auth_cookies` (linha 74) passa a limpar `role` também. Os chamadores `_set_auth_cookies` em `CookieTokenObtainPairView.post` (linha 85), `CookieTokenRefreshView` (116,124) e `exchange_oauth_code` (`auth_views.py:180`) passam `role="staff" if user.is_staff else "tenant"`. No refresh, derivar o user do token (`AccessToken(access)["user_id"]`) para recomputar o role.
- Para o portal do inquilino (OTP): `WhatsAppAuthViewSet.verify_code` (`auth_views.py:108`) hoje retorna `{access, refresh}` em body (linhas 182-189) e NÃO usa cookies. Como o middleware do dashboard precisa distinguir tenant de staff, e o inquilino do portal usa o mesmo `auth-store`, o caminho mais simples e correto é: o tenant NUNCA recebe cookie `role=staff`. Garantir que a verificação OTP, se passar a usar cookies (alinhada ao `exchange`/login), use `_set_auth_cookies(response, access, refresh, role="tenant")`. Se o fluxo OTP continuar token-em-body (mobile), o cookie `role` não é setado e o middleware trata ausência de `role` como tenant por padrão (ver regra do middleware abaixo) — fail-safe.

Frontend — `middleware.ts`:
- Ler `request.cookies.get('role')?.value`.
- Definir o conjunto de rotas administrativas (tudo sob `(dashboard)`: `/`, `/buildings`, `/apartments`, `/tenants`, `/leases`, `/furniture`, `/contract-template`, `/finances`, `/financial`, `/admin`, `/settings`). Regra: se `hasToken && role !== 'staff'` e `path` é rota administrativa → `redirect('/tenant')`. Se `hasToken && role === 'staff'` e `path.startsWith('/tenant')` (exceto `/tenant/login`) → permitir (admin pode inspecionar? decisão: redirect `/` para evitar UI quebrada). Manter a lógica de público/login existente.
- Tratar ausência de `role` como `tenant` (fail-safe — não admin) para não vazar dashboard quando o cookie ainda não propagou.

Frontend — `MainLayout` (`components/layouts/main-layout.tsx`): após carregar `user` (já busca `/auth/me/` na linha 27), se `user && !user.is_staff` renderizar um redirect client-side para `/tenant` (defesa em profundidade; o middleware é a barreira principal). Usar `useRouter().replace('/tenant')` dentro de um `useEffect` guardado por `user?.is_staff === false`.

### 5. Contrato FE↔API

- Resposta de login/exchange/refresh: o body já inclui `user.is_staff` (`auth_views_cookie.py:88-96`, `auth_views.py:174`). Nenhuma mudança de body necessária — o `role` viaja só no cookie. O `auth-store.User` (`store/auth-store.ts:7-13`) já tem `is_staff`; o `MainLayout` usa `user.is_staff`. Sem mudança de tipos.

## Arquivos a criar / modificar

**Backend (modificar):**
- `core/permissions.py` — possivelmente remover `FinancialReadOnly` + entrada do dict `PERMISSION_CLASSES` (só se zero consumidores). Sem novas classes.
- `finances/viewsets/crud_views.py` — import + 9 `permission_classes` para `IsAdminUser`.
- `finances/viewsets/dashboard_views.py` — 2 `permission_classes`.
- `finances/viewsets/installment_payroll_views.py` — 3 `permission_classes`.
- `core/viewsets/financial_views.py` — ~14 `permission_classes` para `IsAdminUser`.
- `core/viewsets/financial_dashboard_views.py:27` — 1 `permission_classes`.
- `core/views.py` — `TenantViewSet.get_queryset` e `LeaseViewSet.get_queryset` escopo por inquilino.
- `core/viewsets/month_advance_views.py` — import `IsAdminUser` de `core.permissions`.
- `core/viewsets/auth_views.py` — import `IsAdminUser` de `core.permissions`; passar `role` em `exchange_oauth_code`.
- `core/viewsets/auth_views_cookie.py` — `_set_auth_cookies(role=...)`, `_clear_auth_cookies` limpa `role`, chamadores passam role.

**Frontend (modificar):**
- `frontend/middleware.ts` — leitura de `role`, redirect tenant→`/tenant` em rotas admin, `/tenant`→OTP login quando não autenticado.
- `frontend/components/layouts/main-layout.tsx` — guard `!user.is_staff` → redirect `/tenant`.

**Testes (criar/estender):**
- `tests/unit/test_permissions_segregation.py` (novo) — escopo de tenants/leases e 403 financeiro.
- Estender testes existentes de finances/core que assumam leitura por não-staff (ajustar expectativas para 403).
- `frontend/components/layouts/__tests__/main-layout.test.tsx` (novo) — guard de papel.
- `frontend/__tests__/middleware.test.ts` (novo, se não existir suite de middleware) — redirect por role.

## TDD — cenários de teste

**Backend (pytest, fronteira = HTTP via APIClient; sem mock de ORM/services):**
- `test_tenant_lists_only_own_tenant_record` — inquilino não-staff em `GET /api/tenants/` recebe só o próprio registro (1 item), não a PII de outros. (regressão do ALTO)
- `test_staff_lists_all_tenants` — staff vê todos (não quebrou o admin).
- `test_tenant_lists_only_own_leases` — inquilino em `GET /api/leases/` recebe só leases onde é `responsible_tenant`. (regressão do ALTO)
- `test_tenant_cannot_retrieve_other_tenant_lease` — `GET /api/leases/{outra}/` → 404 (escopo de queryset).
- `test_tenant_cannot_generate_contract_for_other_lease` — `POST /api/leases/{outra}/generate_contract/` → 404/403.
- `test_tenant_gets_403_on_finances_list` — inquilino em `GET /api/finances/bills/`, `/finances/categories/`, `/finances/reserves/`, `/finance-dashboard/combined_calendar/` → 403. (regressão do ALTO financeiro — prova o bug)
- `test_tenant_gets_403_on_legacy_financial_list` — inquilino em `GET /api/persons/`, `/financial-dashboard/overview/` → 403.
- `test_staff_reads_finances_ok` — staff em todos os acima → 200 (não quebrou o módulo novo).
- `test_superuser_non_staff_is_admin_everywhere` — usuário `is_superuser=True, is_staff=False` é admin (prova a unificação de `IsAdminUser` no `month_advance`/`finances`).
- `test_tenant_portal_still_works` — inquilino em `GET /api/tenant/me/`, `/api/tenant/payments/` → 200 (não quebrou o portal — CUIDADO citado).
- `test_login_sets_role_staff_cookie` — `POST /api/auth/token/` com admin seta cookie `role=staff` e `is_authenticated`.
- `test_otp_verify_sets_role_tenant_cookie` (se o fluxo OTP passar a usar cookies) — `role=tenant`.
- `test_logout_clears_role_cookie` — `POST /api/auth/logout/` limpa `role`.

**Frontend (vitest + MSW na fronteira HTTP):**
- `middleware: tenant role redirected from /buildings to /tenant` — `role=tenant` em rota admin → 307 `/tenant`.
- `middleware: staff role allowed on /finances/bills` — `role=staff` → next().
- `middleware: missing role treated as tenant (fail-safe)` — sem cookie `role` mas com `is_authenticated` em rota admin → redirect `/tenant`.
- `middleware: unauthenticated on /tenant redirects to /tenant/login` (não para `/login` admin).
- `main-layout: non-staff user redirected to /tenant` — `user.is_staff=false` dispara `router.replace('/tenant')`.
- `main-layout: staff user renders dashboard` — `user.is_staff=true` renderiza children (regressão — não quebrou admin).

## Migrations / dados

N/A — nenhuma mudança de schema, nenhuma tabela nova. Apenas `permission_classes`, querysets e cookies. Sem backup necessário, sem RLS nova.

## Constraints (o que NÃO fazer)

- NÃO refatorar o módulo financeiro legado (`financial_views.py`/`financial_dashboard_views.py`/`app/(dashboard)/financial/`) além do swap de `permission_classes` — é deprecated; trocar a classe é mudança mínima, não reescrever lógica.
- NÃO mexer no portal do inquilino `/api/tenant/*` (`tenant_views.py`, `IsTenantUser`/`HasActiveLease`) nem nas rotas FE `/tenant/*` exceto o redirect de login. CUIDADO: não quebrar OTP, PIX, comprovantes, notificações.
- NÃO remover `FinancialReadOnly` se houver QUALQUER consumidor restante (rodar grep amplo incluindo `mobile/`). Verificar `mobile/` antes de qualquer remoção de classe/endpoint — o app Expo consome `/api/`.
- NÃO usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `TODO/FIXME`, re-exports nem shims de compat. Sem `from __future__ import annotations`.
- NÃO setar o cookie `role` como HttpOnly (o middleware Edge precisa lê-lo). É um claim de papel, não um segredo — o JWT continua HttpOnly e é a fonte de verdade no backend.
- NÃO confiar só no middleware: o backend (queryset scope + `IsAdminUser`) é a barreira real; o FE é UX/defesa em profundidade.

## Critérios de aceite (binários)

- [ ] Inquilino não-staff em `GET /api/tenants/` recebe apenas o próprio registro; em `GET /api/leases/` apenas as próprias leases.
- [ ] Inquilino não-staff recebe 403 em todos os endpoints de `finances/` e no financeiro legado do core (list e detail).
- [ ] Staff continua com 200 em finances/core e vê todos os tenants/leases.
- [ ] Superuser sem `is_staff` é tratado como admin em `month_advance` e `finances` (semântica única de `IsAdminUser`).
- [ ] Portal do inquilino (`/api/tenant/*`) continua 200 para inquilino com lease ativa.
- [ ] Login admin seta cookie `role=staff`; logout limpa `role`.
- [ ] `middleware.ts` redireciona tenant (ou role ausente) de rota administrativa para `/tenant`; permite staff.
- [ ] `MainLayout` redireciona `!is_staff` para `/tenant`.
- [ ] Nenhum import de `IsAdminUser` vindo de `rest_framework.permissions` permanece em `core/`.
- [ ] Gate de verificação passa (backend escopado + frontend) com zero erros e zero warnings.

## Gate de verificação

Backend (escopado nos arquivos editados + regressão dirigida de permissões/portal):
```
ruff check && ruff format --check
mypy core/ && pyright
python -m pytest tests/unit/test_permissions_segregation.py tests/ -k "permission or tenant_portal or finances and (403 or staff)"
```
(suite cheia tem flakiness pré-existente de xdist/Redis — rodar escopado; não é bloqueio.)

Frontend:
```
cd frontend && npm run lint && npm run type-check
npm run test:unit -- middleware main-layout
```

## Handoff

Commit sugerido:
```
fix(security): segregate tenant×admin access and gate financial endpoints to is_staff

Scope tenants/leases querysets to the requesting tenant when non-staff, swap
FinancialReadOnly→IsAdminUser across finances/ and legacy core financial viewsets,
unify IsAdminUser on core.permissions, and add a non-HttpOnly `role` cookie so the
Next.js middleware + MainLayout can block tenants from the admin dashboard.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar `MEMORY.md` (entrada nova: "Permission segregation tenant×admin" — querysets escopados + role cookie + IsAdminUser financeiro). O próximo plano pode assumir que: (a) o backend é a barreira de autorização real e o FE confia no cookie `role`; (b) `FinancialReadOnly` está removida OU sem uso nos viewsets administrativos; (c) o portal do inquilino segue isolado em `IsTenantUser`.
