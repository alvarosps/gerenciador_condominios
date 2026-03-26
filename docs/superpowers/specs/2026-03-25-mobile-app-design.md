# Mobile App — Design Spec

**Data:** 2026-03-25
**Status:** Draft

## Resumo

Aplicativo mobile (Android/iOS) para o sistema de gestão de imóveis, com duas experiências baseadas no role do usuário:

- **Inquilino**: ver dados, pagamentos PIX, contrato, histórico, notificações
- **Admin**: dashboard operacional, dashboard financeiro, gestão de inquilinos, ações rápidas

## Decisões Técnicas

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Framework mobile | React Native + Expo | Equipe já domina React/TS, Expo simplifica build/deploy |
| Auth inquilino | CPF/CNPJ + código via WhatsApp | Natural para público brasileiro, sem senhas |
| Provider WhatsApp | Twilio (WhatsApp Business API) | API robusta, suporte a templates de mensagem |
| Pagamento PIX | Estático + comprovante manual (v1) | Sem custos por transação, gateway futuro (v2) |
| Push notifications | Expo Push Notifications | Gratuito, integração trivial com Expo |
| Escopo admin | Operações dia-a-dia + dashboard financeiro | Gestão completa fica no frontend web |
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

**Rate limiting**: máximo 3 códigos por CPF/CNPJ a cada 15 minutos para evitar abuso do Twilio.

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
| **Início** | Home | Resumo: próximo vencimento, valor, status. Alertas: multas, avisos. Atalho rápido para pagar |
| **Pagamentos** | Lista, PIX, Simulação | Pagar aluguel (gerar PIX + enviar comprovante). Simular troca de vencimento. Histórico de pagamentos |
| **Contrato** | Contrato, Imóvel | Ver contrato (PDF). Data de vencimento do contrato. Dados do imóvel |
| **Perfil** | Dados, Config | Dados cadastrais (nome, CPF, telefone). Dependentes. Configurações de notificação. Logout |

### Admin — Tab Bar

| Tab | Telas | Funcionalidades |
|-----|-------|-----------------|
| **Dashboard** | Home | Resumo de ocupação. Inadimplência. Métricas de locação. Comprovantes pendentes |
| **Imóveis** | Lista, Detalhes | Lista de prédios → apartamentos. Detalhes do inquilino. Gerar contrato. Ver locações ativas |
| **Financeiro** | Dashboard | Dashboard financeiro (overview, dívidas, categorias). Parcelas próximas/atrasadas. Resumo mensal |
| **Ações** | Lista, Operações | Marcar aluguel como pago. Aprovar/rejeitar comprovantes. Enviar notificações manuais. Calcular multa |

### Fluxo de Login

Tela unificada com dois caminhos:
- **Admin**: email + senha → tabs admin
- **Inquilino**: CPF/CNPJ + código WhatsApp → tabs tenant

## Regras de Negócio — Tenant Inativo

Quando o lease de um tenant é encerrado (soft-deleted), o tenant ainda pode fazer login, mas em modo read-only:

- **Pode**: ver histórico de pagamentos, ver contrato anterior, ver dados cadastrais, ver notificações
- **Não pode**: gerar PIX, enviar comprovante, simular troca de vencimento
- **Home screen**: exibe mensagem "Seu contrato foi encerrado em DD/MM/YYYY" no lugar do resumo de próximo vencimento
- **Implementação**: `IsTenantUser` permite acesso; endpoints de escrita verificam se o tenant tem lease ativo

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
type: CharField                 # due_reminder, due_today, overdue, proof_approved, proof_rejected, admin_notice, new_proof, contract_expiring
title: CharField
body: TextField
is_read: BooleanField(default=False)
read_at: DateTimeField(null=True)
sent_at: DateTimeField           # quando foi enviada via push
data: JSONField(null=True)       # deep linking metadata (ex: {"screen": "payments", "proof_id": 42})
# AuditMixin (sem SoftDeleteMixin — notificações não são deletáveis pelo usuário)
```

### Alteração em Person (existente)

```
pix_key: CharField(max_length=100, null=True, blank=True)
pix_key_type: CharField(max_length=10, null=True, blank=True)  # cpf / cnpj / email / phone / random
```

### Alteração em FinancialSettings (existente)

```
default_pix_key: CharField(max_length=100, null=True, blank=True)
default_pix_key_type: CharField(max_length=10, null=True, blank=True)  # cpf / cnpj / email / phone / random
```

Usado como fallback para apartamentos sem owner (condomínio próprio).

## Novos Endpoints

### Autenticação WhatsApp

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `POST /api/auth/whatsapp/request/` | POST | Envia código 6 dígitos via WhatsApp | AllowAny |
| `POST /api/auth/whatsapp/verify/` | POST | Valida código, retorna JWT | AllowAny |
| `POST /api/auth/set-password/` | POST | Admin define senha para uso no mobile | IsAdminUser |

### Endpoints do Inquilino

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `GET /api/tenant/me/` | GET | Dados do tenant + apartamento + lease | IsTenantUser |
| `GET /api/tenant/contract/` | GET | PDF do contrato atual | IsTenantUser |
| `GET /api/tenant/payments/` | GET | Histórico de pagamentos (RentPayment) | IsTenantUser |
| `POST /api/tenant/payments/pix/` | POST | Gera código PIX estático | IsTenantUser + HasActiveLease |
| `POST /api/tenant/payments/proof/` | POST | Upload de comprovante (imagem ou PDF) | IsTenantUser + HasActiveLease |
| `GET /api/tenant/payments/proof/{id}/` | GET | Status do comprovante | IsTenantUser |
| `POST /api/tenant/due-date/simulate/` | POST | Simula troca de vencimento | IsTenantUser + HasActiveLease |
| `GET /api/tenant/notifications/` | GET | Lista de notificações | IsTenantUser |
| `PATCH /api/tenant/notifications/{id}/read/` | PATCH | Marca notificação como lida | IsTenantUser |
| `POST /api/tenant/notifications/read-all/` | POST | Marca todas como lidas | IsTenantUser |

### Endpoints do Admin (novos)

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `GET /api/admin/proofs/` | GET | Lista comprovantes pendentes | IsAdminUser |
| `POST /api/admin/proofs/{id}/review/` | POST | Aprovar/rejeitar comprovante | IsAdminUser |

### Device Tokens

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `POST /api/devices/register/` | POST | Registra expo push token | IsAuthenticated |
| `POST /api/devices/unregister/` | POST | Remove token (logout) | IsAuthenticated |

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
| `admin_notice` | Tenant | Manual | Admin envia pelo app |
| `new_proof` | Admin | Evento | Tenant envia comprovante |
| `contract_expiring` | Admin | Cron | 30 dias antes do fim do contrato |

### Implementação

- **Backend**: novo service `notification_service.py` — envio via Expo Push API
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
│   │   ├── _layout.tsx             # Tab navigator
│   │   ├── index.tsx               # Início (resumo + alertas)
│   │   ├── payments/
│   │   │   ├── index.tsx           # Lista pagamentos + atalho pagar
│   │   │   ├── pix.tsx             # Gerar PIX + enviar comprovante
│   │   │   └── simulate.tsx        # Simular troca vencimento
│   │   ├── contract.tsx            # Ver contrato PDF
│   │   └── profile.tsx             # Dados + dependentes + config
│   └── (admin)/                    # Tabs do admin
│       ├── _layout.tsx             # Tab navigator
│       ├── index.tsx               # Dashboard (ocupação + inadimplência)
│       ├── properties/
│       │   ├── index.tsx           # Lista prédios
│       │   └── [id].tsx            # Detalhes prédio → aptos → tenants
│       ├── financial.tsx           # Dashboard financeiro
│       └── actions/
│           ├── index.tsx           # Lista de ações pendentes
│           ├── mark-paid.tsx       # Marcar aluguel como pago
│           └── proofs.tsx          # Aprovar/rejeitar comprovantes
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

- **Propósito**: envio de códigos de verificação para login do inquilino
- **Setup necessário**: conta Twilio, WhatsApp Business Profile verificado, template de mensagem aprovado
- **Template**: "Seu código de verificação é: {{1}}. Válido por 5 minutos."
- **Custo**: ~R$0,30-0,50 por mensagem WhatsApp via Twilio
- **Env vars**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`

### Expo Push Notifications

- **Propósito**: notificações push para lembrete de vencimento, aprovação de comprovante, etc.
- **Setup**: configurar credenciais FCM (Android) e APNs (iOS) no Expo
- **Custo**: gratuito
- **Backend**: HTTP POST para `https://exp.host/--/api/v2/push/send`

## Fora de Escopo (v1)

- Integração com gateway de pagamento (PIX dinâmico com confirmação automática)
- Google OAuth no mobile (admin usa email/senha; pode ser adicionado em v2)
- Cadastro/edição de imóveis pelo app (admin usa web)
- Gestão financeira completa (despesas, cash flow, categorias — admin usa web)
- Chat entre admin e inquilino
- Modo offline / sync
- Multi-idioma (app só em português)
- Migração para S3/object storage (v1 usa filesystem local)
