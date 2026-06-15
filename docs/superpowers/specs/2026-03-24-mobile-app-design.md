# Mobile App — React Native (Expo)

App mobile para Android/iOS com visão de **inquilino** e **admin**, consumindo a API Django existente.

## Decisões

| Decisão | Escolha |
|---------|---------|
| Framework | React Native + Expo (Expo Router, file-based routing) |
| Auth inquilino | CPF + código 6 dígitos via WhatsApp (Twilio) |
| Auth admin | Email + senha (JWT existente) |
| Pagamento PIX | Estático + comprovante manual (v1); gateway futuro (v2) |
| Push notifications | Expo Push Notifications |
| Escopo admin | Operações dia-a-dia + dashboard financeiro |
| Backend | Novos endpoints no Django existente |
| Chave PIX | Por proprietário (`Person.pix_key`), não global |

## Arquitetura

```
┌───────────────────────────────────────────────┐
│           React Native (Expo)                  │
│   Tenant tabs ←── role ──→ Admin tabs          │
│   Expo Router · TanStack Query · Zod · Zustand │
└──────────────────┬────────────────────────────┘
                   │ HTTPS (JWT)
                   ▼
┌───────────────────────────────────────────────┐
│           Django + DRF (existente)             │
│  /api/auth/whatsapp/  (novo)                   │
│  /api/tenant/         (novo)                   │
│  /api/admin/proofs/   (novo)                   │
│  /api/devices/        (novo)                   │
│  /api/                (existente — admin)       │
└──────────┬──────────┬──────────┬──────────────┘
           ▼          ▼          ▼
       PostgreSQL   Twilio    Expo Push
       (existente)  (WhatsApp) (notifications)
```

Um app, dois roles. Login unificado: tipo de usuário define qual conjunto de tabs é exibido.

## Autenticação

### Inquilino — CPF + WhatsApp OTP

1. Inquilino digita CPF → backend busca `Tenant` pelo CPF → verifica telefone cadastrado.
2. Backend cria `WhatsAppVerification` (código 6 dígitos, expira em 5 min, max 3 tentativas).
3. Twilio envia código via WhatsApp Business API (template aprovado).
4. Inquilino digita código → backend valida → cria `User` Django e vincula em `Tenant.user` (no primeiro login) → retorna JWT.
5. App armazena tokens em `expo-secure-store`.

**Rate limiting:** máximo 3 códigos por CPF a cada 15 minutos.

### Admin — JWT existente

Login por email + senha, mesmo fluxo do frontend web. Google OAuth como opção futura no mobile.

## Novos Models

### WhatsAppVerification

| Campo | Tipo | Detalhes |
|-------|------|----------|
| cpf_cnpj | CharField(14) | CPF ou CNPJ do tenant (dígitos apenas, sem formatação — mesmo formato de `Tenant.cpf_cnpj`) |
| code | CharField(6) | Código de verificação |
| phone | CharField(20) | Telefone destino |
| created_at | DateTimeField | Auto |
| expires_at | DateTimeField | created_at + 5 min |
| attempts | IntegerField | Max 3 |
| is_used | BooleanField | Default False |

**Lookup:** o endpoint `/api/auth/whatsapp/request/` recebe CPF/CNPJ, busca `Tenant.objects.get(cpf_cnpj=valor)`. Apenas tenants (não admins) usam esse fluxo. Se o CPF não pertence a nenhum tenant → erro 404.

### TenantUser — NÃO criar model novo

O `Tenant` já possui campo `user = OneToOneField(User, null=True)`. O fluxo de auth do WhatsApp deve:
1. No primeiro login bem-sucedido, criar um `User` Django com `is_staff=False`
2. Atribuir ao `Tenant.user`
3. Nos logins seguintes, buscar `Tenant.user` existente

A permission `IsTenantUser` verifica: `request.user.is_staff == False` e `hasattr(request.user, 'tenant')` (reverse relation do OneToOne).

### DeviceToken

| Campo | Tipo | Detalhes |
|-------|------|----------|
| user | ForeignKey(User) | Dono do device |
| token | CharField(unique) | Expo push token |
| platform | CharField | `ios` / `android` |
| is_active | BooleanField | Default True |
| AuditMixin | | |

### PaymentProof

| Campo | Tipo | Detalhes |
|-------|------|----------|
| tenant | ForeignKey(Tenant) | Quem enviou |
| lease | ForeignKey(Lease) | Locação referente |
| reference_month | DateField | Mês/ano de referência |
| file | FileField | Imagem ou PDF |
| pix_code | TextField | Código PIX usado |
| status | CharField | `pending` / `approved` / `rejected` |
| reviewed_by | ForeignKey(User, null) | Admin que revisou |
| reviewed_at | DateTimeField(null) | Quando revisou |
| rejection_reason | TextField(null) | Motivo da rejeição |
| AuditMixin, SoftDeleteMixin | | |

### Notification

| Campo | Tipo | Detalhes |
|-------|------|----------|
| user | ForeignKey(User) | Destinatário |
| title | CharField | Título |
| body | TextField | Corpo da mensagem |
| type | CharField | `payment_reminder`, `proof_approved`, `proof_rejected`, `admin_notice`, `contract_expiring`, `overdue` |
| data | JSONField(null) | Payload para deep linking |
| is_read | BooleanField | Default False |
| sent_at | DateTimeField | Quando foi enviada |
| AuditMixin | | |

### Alteração em Person (existente)

| Campo | Tipo | Detalhes |
|-------|------|----------|
| pix_key | CharField(null) | Chave PIX do proprietário |
| pix_key_type | CharField(null) | `cpf` / `cnpj` / `email` / `phone` / `random` |

### Alteração em FinancialSettings (existente)

| Campo | Tipo | Detalhes |
|-------|------|----------|
| default_pix_key | CharField(null) | Chave PIX padrão (imóveis sem owner) |
| default_pix_key_type | CharField(null) | Tipo da chave PIX padrão |

## Regras de Negócio — Tenant Inativo

**Como determinar lease ativa:** Lease não tem `end_date`. Uma lease é "ativa" se não foi soft-deleted (`is_deleted=False`). A data de fim do contrato é calculada como `start_date + validity_months`. Lease soft-deleted = contrato encerrado.

**Qual lease retornar:** `/api/tenant/me/` retorna a lease ativa (não-deletada) mais recente do tenant via o M2M `Lease.tenants` (e `Lease.responsible_tenant` quando o inquilino é o responsável). Se houver múltiplas (improvável), usa a com `start_date` mais recente.

Um inquilino cujo contrato (Lease) foi encerrado (soft-deleted) **ainda pode fazer login** no app, mas com funcionalidade limitada:

- **Pode:** ver dados cadastrais, ver contrato anterior (PDF), ver histórico de pagamentos, ver notificações
- **Não pode:** gerar PIX, enviar comprovante, simular troca de vencimento
- **Na tela Início:** exibe mensagem "Seu contrato não está ativo" em vez do resumo de vencimento
- **Lógica:** verificar se o tenant tem lease não-deletada. Se não tem, tabs de pagamento mostram estado vazio com mensagem explicativa

## Novos Endpoints

### Autenticação WhatsApp

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/auth/whatsapp/request/` | POST | Envia código (recebe CPF) | AllowAny |
| `/api/auth/whatsapp/verify/` | POST | Valida código, retorna JWT | AllowAny |

### Tenant (inquilino logado)

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/tenant/me/` | GET | Dados do tenant + apartamento + lease | IsTenantUser |
| `/api/tenant/contract/` | GET | PDF do contrato atual | IsTenantUser |
| `/api/tenant/payments/` | GET | Histórico de pagamentos (RentPayment) | IsTenantUser |
| `/api/tenant/payments/pix/` | POST | Gera código PIX estático | IsTenantUser |
| `/api/tenant/payments/proof/` | POST | Upload de comprovante | IsTenantUser |
| `/api/tenant/payments/proof/{id}/` | GET | Status do comprovante | IsTenantUser |
| `/api/tenant/due-date/simulate/` | POST | Simula troca de vencimento | IsTenantUser |
| `/api/tenant/notifications/` | GET | Lista de notificações | IsTenantUser |

### Admin (novos)

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/admin/proofs/` | GET | Comprovantes pendentes | IsAdminUser |
| `/api/admin/proofs/{id}/review/` | POST | Aprovar/rejeitar comprovante | IsAdminUser |

### Device tokens

| Endpoint | Método | Descrição | Permissão |
|----------|--------|-----------|-----------|
| `/api/devices/register/` | POST | Registra expo push token | IsAuthenticated |
| `/api/devices/unregister/` | POST | Remove token (logout) | IsAuthenticated |

### PIX — Lógica de chave por proprietário

1. Tenant logado → busca Lease → busca Apartment.
2. Se `apartment.owner` existe (kitnet) → usa `owner.pix_key` (campo em `Person`).
3. Se não tem owner (condomínio próprio) → usa `FinancialSettings.default_pix_key` (novo campo).
4. Monta payload EMV com chave do proprietário correto + valor do aluguel.
5. Se nenhuma chave PIX encontrada → retorna erro (admin precisa cadastrar).

## Push Notifications

### Tipos

| Notificação | Destinatário | Trigger | Quando |
|-------------|-------------|---------|--------|
| Lembrete de vencimento | Tenant | Cron | 3 dias antes |
| Dia do vencimento | Tenant | Cron | No dia |
| Aluguel atrasado | Tenant | Cron | 1, 5, 15 dias após |
| Comprovante aprovado | Tenant | Evento | Admin aprova |
| Comprovante rejeitado | Tenant | Evento | Admin rejeita |
| Aviso do admin | Tenant | Manual | Admin envia |
| Novo comprovante | Admin | Evento | Tenant envia |
| Contrato vencendo | Admin | Cron | 30 dias antes |

### Implementação

- **Backend:** `notification_service.py` — envia via Expo Push API. Management command `send_scheduled_notifications` roda via cron.
- **Model:** `Notification` registra tudo (tipo, destinatário, lido, data). Permite tela de histórico no app.
- **Eventos:** signals/services disparam após ações (ex: `PaymentProof.status = approved` → push para tenant).
- **App:** `expo-notifications` para registrar token, receber push, e deep linking (tocar abre tela relevante).

## Navegação do App

### Inquilino — 4 tabs

| Tab | Telas |
|-----|-------|
| **Início** | Resumo (próximo vencimento, valor, status), alertas, atalho para pagar |
| **Pagamentos** | Pagar aluguel (PIX + comprovante), simular troca vencimento, histórico |
| **Contrato** | Ver PDF, data vencimento, dados do imóvel |
| **Perfil** | Dados cadastrais, dependentes, config notificações, logout |

### Admin — 4 tabs

| Tab | Telas |
|-----|-------|
| **Dashboard** | Ocupação, inadimplência, métricas, comprovantes pendentes |
| **Imóveis** | Prédios → apartamentos → tenants, gerar contrato, locações |
| **Financeiro** | Dashboard financeiro (overview, dívidas, categorias), parcelas, resumo mensal |
| **Ações** | Marcar pago, aprovar comprovantes, notificações manuais, calcular multa |

### Login

Tela unificada. Admin: email + senha. Inquilino: CPF + código WhatsApp. Role do user define qual grupo de tabs é exibido.

## Estrutura do Projeto

```
mobile/                          # raiz, ao lado de frontend/
├── app/                         # Expo Router
│   ├── _layout.tsx              # Root (providers, fonts)
│   ├── index.tsx                # Auth redirect
│   ├── login.tsx                # Login unificado
│   ├── (tenant)/                # Tabs inquilino
│   │   ├── _layout.tsx
│   │   ├── index.tsx            # Início
│   │   ├── payments/
│   │   │   ├── index.tsx        # Lista + atalho
│   │   │   ├── pix.tsx          # Gerar PIX + comprovante
│   │   │   └── simulate.tsx     # Simular troca
│   │   ├── contract.tsx         # Ver contrato
│   │   └── profile.tsx          # Perfil
│   └── (admin)/                 # Tabs admin
│       ├── _layout.tsx
│       ├── index.tsx            # Dashboard
│       ├── properties/
│       │   ├── index.tsx        # Prédios
│       │   └── [id].tsx         # Detalhes
│       ├── financial.tsx        # Dashboard financeiro
│       └── actions/
│           ├── index.tsx        # Ações pendentes
│           ├── mark-paid.tsx    # Marcar pago
│           └── proofs.tsx       # Comprovantes
├── components/
│   ├── ui/                      # Design system
│   └── shared/                  # Componentes de negócio
├── lib/
│   ├── api/
│   │   ├── client.ts            # Axios + JWT interceptors
│   │   └── hooks/               # TanStack Query hooks
│   ├── schemas/                 # Zod
│   ├── notifications.ts         # expo-notifications setup
│   └── secure-store.ts          # expo-secure-store wrapper
├── store/
│   └── auth-store.ts            # Zustand
├── app.json
├── package.json
└── tsconfig.json
```

### Dependências principais

- `expo`, `expo-router` — framework + navegação
- `@tanstack/react-query` — cache/sync API
- `zod` — validação
- `zustand` — auth state
- `axios` — HTTP client
- `expo-secure-store` — armazenamento seguro de tokens
- `expo-notifications` — push notifications
- `react-native-qrcode-svg` — QR code do PIX
- `expo-document-picker`, `expo-image-picker` — upload comprovante
- UI library (decisão na implementação): `react-native-paper` ou `tamagui`

## Notas de Implementação

- **Timezone:** todas as notificações cron usam `America/Sao_Paulo`
- **Cron:** management command `send_scheduled_notifications` executado via cron do OS (não Celery) — volume pequeno não justifica Celery
- **UI library:** preferência por `react-native-paper` (Material Design) — decisão final no início da implementação
- **Twilio WhatsApp:** template de mensagem precisa ser aprovado pela Meta antes de usar em produção — durante desenvolvimento, usar Twilio Sandbox

## Fora de Escopo (v1)

- Pagamento PIX com confirmação automática (gateway) — planejado para v2
- Google OAuth no mobile (admin usa email + senha)
- Gestão financeira completa no mobile (despesas, cash flow, categorias — fica no web)
- Cadastro de novos inquilinos/imóveis pelo app (fica no web)
- Chat entre admin e inquilino
- Modo offline / sync
