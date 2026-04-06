# Mobile App — Design Spec

**Data:** 2026-03-29 (rev.4 — atualizado com Compras do Mês)
**Status:** Draft

## Resumo

Aplicativo mobile (Android/iOS) para o sistema de gestão de imóveis, com duas experiências baseadas no role do usuário:

- **Inquilino**: ver dados, pagamentos PIX, contrato, histórico de reajustes, notificações
- **Admin**: dashboard operacional, dashboard financeiro, controle diário, reajuste de aluguel, gestão de inquilinos e locações, ações rápidas

## Decisões Técnicas

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Framework mobile | React Native + Expo | Equipe já domina React/TS, Expo simplifica build/deploy |
| Auth inquilino | CPF/CNPJ + código via WhatsApp | Natural para público brasileiro, sem senhas |
| Provider WhatsApp | Twilio (WhatsApp Business API) | API robusta, suporte a templates de mensagem |
| Pagamento PIX | Estático + comprovante manual (v1) | Sem custos por transação, gateway futuro (v2) |
| Push notifications | Expo Push Notifications | Gratuito, integração trivial com Expo |
| Escopo admin | Operações dia-a-dia + dashboard financeiro + controle diário | Gestão completa (despesas, cash flow, categorias, simulador) fica no frontend web |
| Backend | Endpoints novos no Django existente | Mesmos dados, mesmos models, sem microserviço |
| UI library | `react-native-paper` (preferência) | Material Design 3, boa doc, componentes prontos. Decisão final na implementação |

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                   React Native (Expo)                │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │  Tenant App   │  │  Admin App   │  (mesmo projeto, │
│  │  (role-based) │  │  (role-based) │   tabs diferentes)│
│  └──────┬───────┘  └──────┬───────┘                  │
│         └────────┬────────┘                          │
│                  ▼                                    │
│         Expo Router (file-based)                     │
│         TanStack Query (cache/sync)                  │
│         Zod (validação)                              │
└─────────────────┬───────────────────────────────────┘
                  │ HTTPS
                  ▼
┌─────────────────────────────────────────────────────┐
│              Django + DRF (existente)                 │
│                                                      │
│  /api/tenant/    ← endpoints novos para inquilino    │
│  /api/           ← endpoints existentes (admin)      │
│  /api/auth/whatsapp/  ← auth por CPF + WhatsApp     │
│                                                      │
│  Novos models: DeviceToken, PaymentProof,            │
│    WhatsAppVerification, Notification                 │
│  Reuso: Tenant.user (OneToOneField existente)        │
│                                                      │
│  Endpoints existentes reutilizados pelo admin mobile: │
│    /api/dashboard/, /api/leases/, /api/daily-control/ │
│    /api/financial-dashboard/, /api/rent-payments/      │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌───────┼────────┐
         ▼       ▼        ▼
     PostgreSQL  Twilio   Expo Push
     (existente) (WhatsApp) (notifications)
```

- **Monorepo**: app mobile fica em `mobile/` na raiz do projeto
- **Um app, dois roles**: navegação condicional baseada no tipo de usuário (tenant vs admin)
- **Backend compartilhado**: mesma instância Django, novos endpoints com permissões específicas
- **Reuso de endpoints**: o admin mobile reutiliza a maioria dos endpoints existentes da API (dashboard, leases, financial-dashboard, daily-control, rent-payments). Poucos endpoints novos são necessários para o admin.

## Autenticação

### Admin

Login por email/senha via JWT (simplejwt), mesmo fluxo do frontend web. Tokens armazenados no `expo-secure-store`.

**Google OAuth**: não incluído na v1 mobile. Admins que usam apenas Google OAuth no web precisarão definir uma senha para acessar o app. O endpoint `/api/auth/set-password/` (novo) permite que admins autenticados via web definam senha para uso no mobile. Google OAuth mobile pode ser adicionado em versão futura.

### Inquilino

Fluxo novo baseado em CPF/CNPJ + código WhatsApp:

```
1. Inquilino abre app → tela de login → digita CPF ou CNPJ
2. Backend busca Tenant pelo cpf_cnpj → verifica telefone cadastrado
3. Backend normaliza Tenant.phone para E.164 (+55...) antes de enviar
   - Ex: "(11) 99999-8888" → "+5511999998888"
   - Se telefone não cadastrado ou inválido → retorna 400 "Telefone não cadastrado"
4. Backend envia código 6 dígitos via WhatsApp (Twilio)
5. Inquilino digita código → backend valida
6. Se Tenant.user é null → cria User Django (is_staff=False) e vincula ao Tenant
7. Backend retorna JWT (mesmo simplejwt)
8. App armazena tokens no SecureStore
```

**Normalização de telefone**: o service de WhatsApp inclui uma função `normalize_phone_to_e164(phone: str) -> str` que limpa a string do `Tenant.phone` (remove parênteses, espaços, traços) e prefixa com `+55` se necessário. Twilio exige formato E.164.

**Reutilização do campo existente**: `Tenant` já possui `user = OneToOneField(User, null=True)` — NÃO criar model novo. No primeiro login bem-sucedido, se `tenant.user` é null, cria-se um `User` Django com `is_staff=False` e vincula ao tenant existente.

**Rate limiting** (duas proteções independentes):
- **Geração**: máximo 3 códigos por CPF/CNPJ a cada 15 minutos (evita abuso do Twilio)
- **Tentativas**: máximo 3 tentativas erradas por código (campo `attempts` no `WhatsAppVerification`). Após 3 erros, código é invalidado e o tenant deve solicitar um novo.

### Token Refresh (Mobile)

O app mobile usa o mesmo padrão do frontend web: axios interceptor que detecta 401, faz refresh automático via `/api/auth/token/refresh/`, e re-executa a request original. Diferença: ao retornar do background (app resume), o interceptor verifica se o access token expirou antes da primeira request — se sim, faz refresh proativamente. Tokens são persistidos no `expo-secure-store` (não localStorage como no web).

### Permission: IsTenantUser

Nova permission class em `core/permissions.py`:

```python
class IsTenantUser(BasePermission):
    """Permite acesso apenas a inquilinos autenticados com registro não-deletado."""
    def has_permission(self, request, view):
        if not (request.user.is_authenticated and not request.user.is_staff):
            return False
        tenant = getattr(request.user, 'tenant_profile', None)
        return tenant is not None and not tenant.is_deleted


class HasActiveLease(BasePermission):
    """Permite acesso apenas a tenants com lease ativo (não soft-deleted)."""
    def has_permission(self, request, view):
        tenant = getattr(request.user, 'tenant_profile', None)
        if tenant is None:
            return False
        return tenant.leases.filter(is_deleted=False).exists()
```

- `IsTenantUser`: usado em TODOS os endpoints tenant (read + write). Verifica que o tenant não foi soft-deleted.
- `HasActiveLease`: composto junto com `IsTenantUser` nos endpoints de escrita (PIX, proof upload, simulação de vencimento). Retorna 403 se não há lease ativo.
- Cada endpoint tenant usa `request.user.tenant_profile` para filtrar dados — o inquilino só acessa seus próprios dados.

## Telas e Navegação

### Inquilino — Tab Bar

| Tab | Telas | Funcionalidades |
|-----|-------|-----------------|
| **Início** | Home | Resumo: próximo vencimento, valor atual, status de pagamento. Alerta de reajuste pendente (se houver `pending_rental_value`). Alertas: multas, avisos. Atalho rápido para pagar |
| **Pagamentos** | Lista, PIX, Simulação | Pagar aluguel (gerar PIX + enviar comprovante). Simular troca de vencimento. Histórico de pagamentos. Histórico de reajustes de aluguel |
| **Contrato** | Contrato, Imóvel | Ver contrato (PDF). Data de vencimento do contrato. Dados do imóvel (endereço, prédio, valor atual e próximo se houver reajuste pendente) |
| **Perfil** | Dados, Config | Dados cadastrais (nome, CPF, telefone). Dependentes. Configurações de notificação. Logout |

### Admin — Tab Bar (5 tabs)

| Tab | Telas | Funcionalidades |
|-----|-------|-----------------|
| **Dashboard** | Home | Resumo de ocupação. Inadimplência (late_payment_summary). Métricas de locação (lease_metrics). Comprovantes pendentes de aprovação. **Alertas de reajuste** (locações elegíveis para reajuste anual) |
| **Imóveis** | Lista, Detalhes | Lista de prédios → apartamentos (com `rental_value` e `rental_value_double`). Detalhes do inquilino. Gerar contrato. Ver locações ativas. **Criar nova locação** |
| **Financeiro** | Dashboard, Controle Diário, Compras do Mês | Dashboard financeiro (overview, dívidas por pessoa/tipo, categorias, parcelas). **Controle diário**: entradas/saídas do dia (incluindo person_schedule), resumo mensal, marcar como pago, pular despesa (ExpenseMonthSkip), pagamento de pessoa com valor sugerido. **Compras do mês**: resumo de novas compras no mês por tipo (cartão, empréstimos, contas, pontuais, fixas) e por categoria |
| **Ações** | Lista, Operações | Marcar aluguel como pago. Aprovar/rejeitar comprovantes. **Aplicar reajuste de aluguel** (com envio de WhatsApp ao inquilino). Enviar notificações manuais. Calcular multa por atraso |
| **Notificações** | Lista | Histórico de notificações do admin (novos comprovantes, contratos vencendo). Badge de não lidas |

### Fluxo de Login

Tela unificada com dois caminhos:
- **Admin**: email + senha → tabs admin
- **Inquilino**: CPF/CNPJ + código WhatsApp → tabs tenant

## Regras de Negócio — Tenant Inativo

Quando o lease de um tenant é encerrado (soft-deleted), o tenant ainda pode fazer login, mas em modo read-only:

- **Pode**: ver histórico de pagamentos, ver contrato anterior, ver dados cadastrais, ver notificações, ver histórico de reajustes
- **Não pode**: gerar PIX, enviar comprovante, simular troca de vencimento
- **Home screen**: exibe mensagem "Seu contrato foi encerrado em DD/MM/YYYY" no lugar do resumo de próximo vencimento
- **Implementação**: `IsTenantUser` permite acesso; endpoints de escrita verificam se o tenant tem lease ativo via `HasActiveLease`

## Regras de Negócio — Reajuste de Aluguel

O sistema de reajuste já existe no backend (`RentAdjustmentService`, `IPCAService`). O mobile expõe isso para o admin:

### Fluxo Admin: Aplicar Reajuste

```
1. Dashboard mostra alertas de locações elegíveis (12+ meses sem reajuste)
2. Admin abre ação "Aplicar Reajuste" → seleciona lease
3. App sugere percentual baseado no IPCA (via IPCAService.get_adjustment_percentage)
4. Admin confirma percentual, data de aplicação, e opção "atualizar preços do apartamento"
5. Backend aplica reajuste via RentAdjustmentService.apply_adjustment()
6. Se data futura → cria pending_rental_value no lease
7. Se data atual/passada → atualiza rental_value diretamente
8. Backend envia WhatsApp ao inquilino informando o reajuste (novo template Twilio)
9. Cria Notification push para o inquilino
```

### WhatsApp de Reajuste

Novo template Twilio para notificação de reajuste:
- **Template**: "Informamos que o aluguel do imóvel {{1}} será reajustado de R$ {{2}} para R$ {{3}} ({{4}}%) a partir de {{5}}."
- O envio usa o mesmo `whatsapp_service.py` com `normalize_phone_to_e164`
- Requer aprovação de template adicional no Twilio

### Fluxo Tenant: Ver Reajuste

- Home screen mostra alerta se `lease.pending_rental_value` existe: "Seu aluguel será reajustado para R$ X.XXX,XX a partir de DD/MM/YYYY"
- Histórico de reajustes visível na tab Pagamentos (lista de `RentAdjustment` do lease)
- Notificação push + WhatsApp recebidos quando admin aplica reajuste

## Regras de Negócio — Controle Diário (Admin)

Reutiliza os endpoints existentes do `DailyControlViewSet`:

- `GET /api/daily-control/breakdown/?year=2026&month=3` — entradas/saídas dia a dia
- `GET /api/daily-control/summary/?year=2026&month=3` — resumo mensal (esperado vs realizado)
- `POST /api/daily-control/mark_paid/` — marcar item como pago

**IMPORTANTE — Correção de permissão necessária**: `DailyControlViewSet` atualmente usa `permission_classes = [IsAuthenticated]`. Como inquilinos agora terão JWT válido, isso permitiria que tenants acessem o controle diário. Antes do lançamento mobile, alterar para `permission_classes = [IsAdminUser]` para restringir ao admin. Mesma correção pode ser necessária em outros viewsets financeiros que usam `IsAuthenticated` em vez de `IsAdminUser` ou `FinancialReadOnly`.

### Tela Mobile

- **Cards resumo**: total entradas, total saídas, saldo do mês (esperado vs realizado)
- **Navegação por mês**: setas prev/next como no frontend web
- **Lista do dia**: agrupada por data, cada item mostra descrição, valor, status (pago/pendente), pessoa/prédio
- **Tipos de saída**: installment, expense, one_time, credit_card, **person_schedule** (novo tipo com pagamento por pessoa)
- **Ação rápida**: swipe ou tap para marcar como pago. Para `person_schedule`, abre modal com:
  - Esperado até dia X, já pago no mês, valor sugerido (esperado - pago)
  - Input para valor manual
  - Usa `PersonPaymentScheduleService.get_suggested_payment()`
- **Skip de despesa**: possibilidade de pular uma despesa recorrente em um mês específico (cria `ExpenseMonthSkip`)
- **Filtros**: por pessoa, prédio, tipo (entrada/saída), status (pago/pendente)

## Regras de Negócio — Criar Locação (Admin)

O admin pode criar uma nova locação pelo mobile. Reutiliza o endpoint existente `POST /api/leases/`.

### Formulário Mobile (simplificado)

Campos obrigatórios:
- Apartamento (select — `GET /api/apartments/?is_rented=false` para listar disponíveis)
- Inquilino responsável (select com busca — `GET /api/tenants/?search=`)
- Data início
- Meses de validade
- Valor do aluguel (auto-preenchido: `apartment.rental_value` para 1 tenant, `apartment.rental_value_double` para 2 tenants quando disponível — mesma lógica do LeaseSerializer)

Campos opcionais:
- Segundo inquilino (se aplicável — atualiza `number_of_tenants` e auto-atualiza valor)
- Dependente residente
- Depósito, taxa de limpeza paga, tag pago

**Não incluído no mobile**: terminar locação, transferir locação (operações mais complexas, ficam no web).

## Novos Models no Backend

### WhatsAppVerification

```
cpf_cnpj: CharField(20)        # CPF ou CNPJ (mesmo formato do Tenant.cpf_cnpj)
code: CharField(6)              # código 6 dígitos
phone: CharField(20)            # telefone destino
created_at: DateTimeField
expires_at: DateTimeField       # created_at + 5 min
attempts: IntegerField(default=0)  # max 3
is_used: BooleanField(default=False)

class Meta:
    indexes = [
        models.Index(fields=['cpf_cnpj', 'is_used', 'expires_at'])
    ]
```

Nota: NÃO usar AuditMixin/SoftDeleteMixin — registros de verificação são efêmeros, podem ser limpos periodicamente.

### DeviceToken

```
user: ForeignKey(User)
token: CharField(unique)        # expo push token
platform: CharField             # ios / android
is_active: BooleanField(default=True)
# AuditMixin (view deve setar created_by=request.user no register)
```

### PaymentProof

```
lease: ForeignKey(Lease)        # tenant derivado via lease.responsible_tenant (sem FK redundante)
reference_month: DateField      # mês/ano de referência
file: FileField(upload_to='payment_proofs/%Y/%m/')  # ver seção Storage
pix_code: TextField             # código PIX usado
status: CharField               # pending / approved / rejected
reviewed_by: ForeignKey(User, null=True)
reviewed_at: DateTimeField(null=True)
rejection_reason: TextField(null=True)
# AuditMixin, SoftDeleteMixin
```

Nota: sem FK direto para Tenant — o tenant é derivado de `proof.lease.responsible_tenant`. Evita denormalização e inconsistência (DRY).

### Notification

```
recipient: ForeignKey(User)
type: CharField                 # due_reminder, due_today, overdue, proof_approved, proof_rejected,
                                # admin_notice, new_proof, contract_expiring, rent_adjustment
title: CharField
body: TextField
is_read: BooleanField(default=False)
read_at: DateTimeField(null=True)
sent_at: DateTimeField           # quando foi enviada via push
data: JSONField(null=True)       # deep linking metadata (ex: {"screen": "payments", "proof_id": 42})
# AuditMixin (sem SoftDeleteMixin — notificações não são deletáveis pelo usuário)
```

### Alteração em Person (existente) — REQUER MIGRAÇÃO

```
pix_key: CharField(max_length=100, null=True, blank=True)
pix_key_type: CharField(max_length=10, null=True, blank=True)  # cpf / cnpj / email / phone / random
```

Estes campos NÃO existem ainda no model. Requer nova migração (próxima após 0030).

### Alteração em FinancialSettings (existente) — REQUER MIGRAÇÃO

```
default_pix_key: CharField(max_length=100, null=True, blank=True)
default_pix_key_type: CharField(max_length=10, null=True, blank=True)  # cpf / cnpj / email / phone / random
```

Usado como fallback para apartamentos sem owner (condomínio próprio). Estes campos NÃO existem ainda. Requer nova migração. O endpoint PIX depende destes campos — devem ser criados antes da implementação do fluxo PIX.

## Regras de Negócio — Compras do Mês (Admin)

Reutiliza o endpoint existente `GET /api/financial-dashboard/monthly_purchases/?year=2026&month=3`.

Mostra novas compras introduzidas no mês, agrupadas em 5 tipos:
- **Compras no cartão** (card_purchases) — primeira parcela vence no mês
- **Empréstimos** (loans) — bancários/pessoais, primeira parcela no mês
- **Contas** (utility_bills) — água/luz, data da despesa no mês
- **Pontuais** (one_time_expenses) — compras únicas no mês
- **Fixas** (fixed_expenses) — despesas recorrentes ativas

Também agrega por categoria de despesa (com percentual e cor).

### Tela Mobile

- **Navegação por mês**: setas prev/next
- **Cards resumo**: total por tipo (5 cards com ícone e valor)
- **Lista colapsável**: accordion por tipo com detalhes dos itens (descrição, pessoa, valor, parcelas)
- **Read-only**: sem ações de escrita nesta tela

## Models Existentes Relevantes para o Mobile (não requerem alteração)

Estes models já existem e são consumidos pelo admin mobile via endpoints existentes:

### PersonPaymentSchedule (migration 0030)

```
person: ForeignKey(Person)
reference_month: DateField          # primeiro dia do mês (2026-03-01)
due_day: PositiveSmallIntegerField  # dia do pagamento (1-31)
amount: DecimalField(12,2)
# AuditMixin, SoftDeleteMixin
# Unique: (person, reference_month, due_day) onde is_deleted=False
```

Usado no controle diário para agrupar saídas de uma pessoa em cronogramas de pagamento. O `PersonPaymentScheduleService` calcula totais, sugere valores de pagamento, e verifica status.

### ExpenseMonthSkip (migration 0030)

```
expense: ForeignKey(Expense)
reference_month: DateField          # mês a ser pulado
# AuditMixin (sem SoftDeleteMixin)
# Unique: (expense, reference_month)
```

Marca uma despesa como não cobrada em um mês específico. Respeitado por CashFlowService, FinancialDashboardService, e DailyControlService.

### RentAdjustment (migration 0023)

```
lease: ForeignKey(Lease)
adjustment_date: DateField
percentage: DecimalField
previous_value: DecimalField
new_value: DecimalField
apartment_updated: BooleanField
# AuditMixin
```

### IPCAIndex (migration 0028)

```
reference_month: DateField(unique)
value: DecimalField
fetched_at: DateTimeField
```

Índice IPCA do IBGE para cálculo de reajuste de aluguel.

## Endpoints — Visão Completa

### Endpoints NOVOS (a criar)

#### Autenticação WhatsApp

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `POST /api/auth/whatsapp/request/` | POST | Envia código 6 dígitos via WhatsApp | AllowAny |
| `POST /api/auth/whatsapp/verify/` | POST | Valida código, retorna JWT | AllowAny |
| `POST /api/auth/set-password/` | POST | Admin define senha para uso no mobile | IsAdminUser |

#### Endpoints do Inquilino

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `GET /api/tenant/me/` | GET | Dados do tenant + apartamento + lease + pending_rental_value | IsTenantUser |
| `GET /api/tenant/contract/` | GET | PDF do contrato atual | IsTenantUser |
| `GET /api/tenant/payments/` | GET | Histórico de pagamentos (RentPayment) | IsTenantUser |
| `GET /api/tenant/rent-adjustments/` | GET | Histórico de reajustes do lease ativo | IsTenantUser |
| `POST /api/tenant/payments/pix/` | POST | Gera código PIX estático | IsTenantUser + HasActiveLease |
| `POST /api/tenant/payments/proof/` | POST | Upload de comprovante (imagem ou PDF) | IsTenantUser + HasActiveLease |
| `GET /api/tenant/payments/proof/{id}/` | GET | Status do comprovante | IsTenantUser |
| `POST /api/tenant/due-date/simulate/` | POST | Simula troca de vencimento | IsTenantUser + HasActiveLease |
| `GET /api/tenant/notifications/` | GET | Lista de notificações | IsTenantUser |
| `PATCH /api/tenant/notifications/{id}/read/` | PATCH | Marca notificação como lida | IsTenantUser |
| `POST /api/tenant/notifications/read-all/` | POST | Marca todas como lidas | IsTenantUser |

#### Endpoints Admin (novos)

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `GET /api/admin/proofs/` | GET | Lista comprovantes pendentes | IsAdminUser |
| `POST /api/admin/proofs/{id}/review/` | POST | Aprovar/rejeitar comprovante | IsAdminUser |
| `POST /api/admin/whatsapp/send/` | POST | Envia mensagem WhatsApp para tenant (reajuste, aviso manual) | IsAdminUser |

#### Device Tokens

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `POST /api/devices/register/` | POST | Registra expo push token | IsAuthenticated |
| `POST /api/devices/unregister/` | POST | Remove token (logout) | IsAuthenticated |

### Endpoints EXISTENTES reutilizados pelo Admin Mobile

O admin mobile consome estes endpoints que já existem — **sem nenhuma alteração no backend**:

| Endpoint existente | Uso no admin mobile |
|-------------------|---------------------|
| `GET /api/dashboard/financial_summary/` | Card de resumo financeiro |
| `GET /api/dashboard/late_payment_summary/` | Inadimplência no dashboard |
| `GET /api/dashboard/lease_metrics/` | Métricas de locação |
| `GET /api/dashboard/building_statistics/` | Estatísticas por prédio |
| `GET /api/dashboard/rent_adjustment_alerts/` | Alertas de reajuste elegível |
| `POST /api/dashboard/mark_rent_paid/` | Marcar aluguel como pago |
| `GET /api/buildings/` | Lista de prédios |
| `GET /api/apartments/` | Lista de apartamentos (com filtros) |
| `GET /api/tenants/` | Lista/busca de inquilinos |
| `GET /api/leases/` | Lista de locações (com filtros active/expired/expiring) |
| `POST /api/leases/` | Criar nova locação |
| `POST /api/leases/{id}/generate_contract/` | Gerar contrato PDF |
| `GET /api/leases/{id}/calculate_late_fee/` | Calcular multa por atraso |
| `POST /api/leases/{id}/adjust_rent/` | Aplicar reajuste de aluguel |
| `GET /api/leases/{id}/rent_adjustments/` | Histórico de reajustes |
| `GET /api/financial-dashboard/overview/` | Overview financeiro |
| `GET /api/financial-dashboard/debt_by_person/` | Dívidas por pessoa |
| `GET /api/financial-dashboard/debt_by_type/` | Dívidas por tipo |
| `GET /api/financial-dashboard/upcoming_installments/` | Parcelas próximas |
| `GET /api/financial-dashboard/overdue_installments/` | Parcelas atrasadas |
| `GET /api/financial-dashboard/category_breakdown/` | Despesas por categoria |
| `GET /api/financial-dashboard/monthly_purchases/` | Compras do mês (por tipo e por categoria) |
| `GET /api/daily-control/breakdown/` | Controle diário — entradas/saídas |
| `GET /api/daily-control/summary/` | Controle diário — resumo mensal |
| `POST /api/daily-control/mark_paid/` | Controle diário — marcar como pago |
| `GET /api/rent-payments/` | Lista de pagamentos de aluguel |
| `GET /api/person-payment-schedules/` | Lista de cronogramas de pagamento por pessoa |
| `GET /api/person-payment-schedules/person_month_total/` | Totais do mês por pessoa (devido, pago, pendente) |
| `POST /api/person-payment-schedules/bulk_configure/` | Configurar cronograma de pagamento (admin) |
| `GET /api/expense-month-skips/` | Lista de despesas puladas no mês |
| `POST /api/expense-month-skips/` | Pular despesa em um mês específico |
| `DELETE /api/expense-month-skips/{id}/` | Remover skip de despesa |

### Lógica PIX

O endpoint `/api/tenant/payments/pix/` monta o payload EMV do PIX:

1. Tenant logado → busca Lease ativo → busca Apartment
2. Se `apartment.owner` existe (kitnet) → usa `owner.pix_key` / `owner.pix_key_type`
3. Se não tem owner (condomínio próprio) → usa `FinancialSettings.default_pix_key` / `default_pix_key_type`
4. Se nenhuma chave PIX encontrada → retorna `400 Bad Request` com mensagem "Chave PIX não cadastrada. Entre em contato com o administrador."
5. Monta payload EMV com chave do proprietário correto + valor do aluguel
6. Retorna: código copia-e-cola + dados para QR code

Cada proprietário de kitnet recebe na sua própria chave PIX.

## Push Notifications

### Tipos de Notificação

| Tipo | Destinatário | Trigger | Quando |
|------|-------------|---------|--------|
| `due_reminder` | Tenant | Cron | 3 dias antes do vencimento |
| `due_today` | Tenant | Cron | No dia do vencimento |
| `overdue` | Tenant | Cron | 1, 5, 15 dias após vencimento |
| `proof_approved` | Tenant | Evento | Admin aprova comprovante |
| `proof_rejected` | Tenant | Evento | Admin rejeita comprovante |
| `rent_adjustment` | Tenant | Evento | Admin aplica reajuste (push + WhatsApp) |
| `admin_notice` | Tenant | Manual | Admin envia pelo app |
| `new_proof` | Admin | Evento | Tenant envia comprovante |
| `contract_expiring` | Admin | Cron | 30 dias antes do fim do contrato |
| `adjustment_eligible` | Admin | Cron | Locação atingiu 12 meses sem reajuste (complementar ao polling via `rent_adjustment_alerts/` — o cron envia push proativo, o endpoint é para consulta ativa no dashboard) |

### Implementação

- **Backend**: novo service `notification_service.py` — envio via Expo Push API
- **WhatsApp service**: `whatsapp_service.py` — envio de mensagens via Twilio (auth codes + reajustes + avisos manuais)
- **Scheduled**: Django management command `send_scheduled_notifications` — roda via cron do OS
- **Event-driven**: notificações por evento disparam no service após a ação
- **App**: `expo-notifications` para registrar token e receber push
- **Deep linking**: tocar na notificação abre a tela relevante (usa campo `data` do Notification)

### Idempotência do Cron

O management command `send_scheduled_notifications` é idempotente:
- Antes de enviar, verifica se já existe um `Notification` com mesmo `type`, `recipient`, e `sent_at` no mesmo dia
- Se já existe, pula o envio (evita duplicatas se cron rodar múltiplas vezes)
- Cada execução processa apenas tenants com lease ativo
- Log de cada notificação enviada/pulada para debugging

## Storage (Comprovantes)

Comprovantes de pagamento (`PaymentProof.file`) são armazenados no filesystem local em `MEDIA_ROOT`:

```
media/
  payment_proofs/
    2026/
      03/
        proof_123.jpg
        proof_124.pdf
```

- **v1**: filesystem local via Django `FileField` com `upload_to='payment_proofs/%Y/%m/'`
- **Futuro**: migrar para S3/object storage quando necessário (basta mudar `DEFAULT_FILE_STORAGE`)
- **Servido via**: `MEDIA_URL` com proteção — endpoint DRF que verifica permissão antes de servir o arquivo (não expor media/ diretamente)
- **Limites**: max 10MB por arquivo, aceita apenas JPEG, PNG, PDF
- **Upload no app**: `expo-image-picker` (câmera + galeria) e `expo-document-picker` (PDF). Tela de upload oferece ambas opções.

## Estrutura do Projeto Mobile

```
mobile/
├── app/                            # Expo Router (file-based routing)
│   ├── _layout.tsx                 # Root layout (providers, fonts)
│   ├── index.tsx                   # Redirect: auth check → login ou tabs
│   ├── login.tsx                   # Tela unificada de login
│   ├── (tenant)/                   # Tabs do inquilino
│   │   ├── _layout.tsx             # Tab navigator (4 tabs)
│   │   ├── index.tsx               # Início (resumo + alertas + reajuste pendente)
│   │   ├── payments/
│   │   │   ├── index.tsx           # Lista pagamentos + atalho pagar
│   │   │   ├── pix.tsx             # Gerar PIX + enviar comprovante
│   │   │   ├── simulate.tsx        # Simular troca vencimento
│   │   │   └── adjustments.tsx     # Histórico de reajustes
│   │   ├── contract.tsx            # Ver contrato PDF + dados imóvel
│   │   └── profile.tsx             # Dados + dependentes + config notificações
│   └── (admin)/                    # Tabs do admin
│       ├── _layout.tsx             # Tab navigator (5 tabs)
│       ├── index.tsx               # Dashboard (ocupação + inadimplência + alertas reajuste)
│       ├── properties/
│       │   ├── index.tsx           # Lista prédios → apartamentos
│       │   ├── [id].tsx            # Detalhes prédio → aptos → tenants
│       │   └── new-lease.tsx       # Criar nova locação
│       ├── financial/
│       │   ├── index.tsx           # Dashboard financeiro (overview, dívidas, categorias)
│       │   ├── daily.tsx           # Controle diário (entradas/saídas, marcar pago, skip despesa, pagamento pessoa)
│       │   └── purchases.tsx       # Compras do mês (resumo por tipo e categoria, read-only)
│       ├── actions/
│       │   ├── index.tsx           # Lista de ações pendentes
│       │   ├── mark-paid.tsx       # Marcar aluguel como pago
│       │   ├── proofs.tsx          # Aprovar/rejeitar comprovantes
│       │   └── rent-adjustment.tsx # Aplicar reajuste (com WhatsApp ao inquilino)
│       └── notifications.tsx       # Notificações do admin
├── components/
│   ├── ui/                         # Design system (botões, inputs, cards)
│   └── shared/                     # Componentes de negócio compartilhados
├── lib/
│   ├── api/
│   │   ├── client.ts               # Axios + JWT interceptors (refresh on 401 + app resume)
│   │   └── hooks/                  # TanStack Query hooks
│   ├── schemas/                    # Zod schemas
│   ├── notifications.ts           # Setup expo-notifications
│   └── secure-store.ts            # Wrapper expo-secure-store
├── store/
│   └── auth-store.ts              # Zustand (user, role, tokens)
├── app.json                        # Expo config
├── package.json
└── tsconfig.json
```

### Dependências Principais

- `expo` + `expo-router` — navegação file-based
- `@tanstack/react-query` — cache/sync
- `zod` — validação
- `zustand` — auth state
- `axios` — HTTP client
- `expo-secure-store` — armazenamento seguro de tokens
- `expo-notifications` — push notifications
- `react-native-qrcode-svg` — QR code do PIX
- `expo-image-picker` — upload comprovante (câmera + galeria)
- `expo-document-picker` — upload comprovante (PDF)
- `react-native-paper` — UI components (preferência)

## Integrações Externas

### Twilio (WhatsApp Business API)

- **Propósito**: (1) códigos de verificação para login, (2) notificação de reajuste de aluguel, (3) avisos manuais do admin
- **Setup necessário**: conta Twilio, WhatsApp Business Profile verificado, templates de mensagem aprovados
- **Templates** (requerem aprovação individual):
  1. Auth: "Seu código de verificação é: {{1}}. Válido por 5 minutos."
  2. Reajuste: "Informamos que o aluguel do imóvel {{1}} será reajustado de R$ {{2}} para R$ {{3}} ({{4}}%) a partir de {{5}}."
  3. Aviso: "{{1}}" (template genérico para avisos do admin — texto livre)
- **Custo**: ~R$0,30-0,50 por mensagem WhatsApp via Twilio
- **Env vars**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`

### Expo Push Notifications

- **Propósito**: notificações push para lembrete de vencimento, aprovação de comprovante, reajuste, etc.
- **Setup**: configurar credenciais FCM (Android) e APNs (iOS) no Expo
- **Custo**: gratuito
- **Backend**: HTTP POST para `https://exp.host/--/api/v2/push/send`

## Mapeamento Features Existentes → Mobile

Referência de quais features do sistema atual são expostas no mobile e quais ficam apenas no web:

### No Mobile (Admin)

| Feature | Endpoint(s) | Notas |
|---------|-------------|-------|
| Dashboard (ocupação, inadimplência, métricas) | `/api/dashboard/*` | Reutiliza existentes |
| Alertas de reajuste | `/api/dashboard/rent_adjustment_alerts/` | Reutiliza existente |
| Lista prédios/apartamentos | `/api/buildings/`, `/api/apartments/` | Read-only no mobile |
| Lista inquilinos | `/api/tenants/` | Read-only no mobile |
| Lista/filtro locações | `/api/leases/` | Reutiliza existente com filtros |
| Criar locação | `POST /api/leases/` | Formulário simplificado no mobile |
| Gerar contrato | `POST /api/leases/{id}/generate_contract/` | Reutiliza existente |
| Calcular multa | `GET /api/leases/{id}/calculate_late_fee/` | Reutiliza existente |
| Aplicar reajuste | `POST /api/leases/{id}/adjust_rent/` | Reutiliza existente + WhatsApp |
| Marcar aluguel pago | `POST /api/dashboard/mark_rent_paid/` | Reutiliza existente |
| Dashboard financeiro | `/api/financial-dashboard/*` | Reutiliza existentes |
| Compras do mês | `/api/financial-dashboard/monthly_purchases/` | Reutiliza existente (resumo por tipo e categoria, read-only) |
| Controle diário | `/api/daily-control/*` | Reutiliza existentes (agora integra person_schedule e expense skips) |
| Pagamento de pessoa (controle diário) | `/api/person-payment-schedules/*` | Reutiliza existentes (person_month_total, bulk_configure) |
| Skip de despesa (controle diário) | `/api/expense-month-skips/*` | Reutiliza existentes (CRUD) |
| Aprovar comprovantes | `/api/admin/proofs/*` | **Novo endpoint** |

### Apenas no Web (não no mobile)

| Feature | Motivo |
|---------|--------|
| CRUD completo de despesas/incomes | Formulários complexos, melhor em tela grande (exceto: skip de despesa e configuração de cronograma de pagamento são acessíveis via controle diário mobile) |
| Avanço/fechamento de mês (MonthSnapshot) | Operação administrativa complexa com validação de pendências, snapshots, e rollback — web only |
| Cash flow projection (12 meses) | Gráfico complexo, melhor em tela grande |
| Simulador financeiro (what-if) | Interface complexa de cenários |
| Editor de contrato (WYSIWYG/código) | Impossível em mobile |
| Gestão de categorias de despesas | Operação rara, admin web |
| Gestão de cartões de crédito | Operação rara, admin web |
| Gestão de pessoas (Person CRUD) | Operação rara, admin web |
| Employee payments | Operação rara, admin web |
| Person payments/incomes | Operação rara, admin web |
| Financial settings | Operação rara, admin web |
| Terminar/transferir locação | Operação complexa, admin web (endpoints `terminate/` e `transfer/` existem no LeaseViewSet mas intencionalmente não expostos no mobile) |
| CRUD de prédios/apartamentos/mobília | Operação rara, admin web |
| Export Excel/CSV | Melhor em desktop |
| Regras de contrato (ContractRule) | Operação rara, admin web |
| Configuração de locador (Landlord) | Operação rara, admin web |

## Fora de Escopo (v1)

- Integração com gateway de pagamento (PIX dinâmico com confirmação automática)
- Google OAuth no mobile (admin usa email/senha; pode ser adicionado em v2)
- Cadastro/edição de imóveis pelo app (admin usa web)
- Gestão financeira completa — despesas, cash flow, categorias, simulador (admin usa web)
- Chat entre admin e inquilino
- Modo offline / sync
- Multi-idioma (app só em português)
- Migração para S3/object storage (v1 usa filesystem local)
- Terminar/transferir locação (admin usa web)
