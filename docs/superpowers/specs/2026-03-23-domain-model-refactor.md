# Domain Model Refactor — Single Source of Truth

**Data:** 2026-03-23
**Status:** Draft
**Escopo:** Building, Apartment, Lease, Tenant, Furniture

## Problema

O sistema atual tem campos duplicados entre Apartment, Lease e Tenant sem sincronização consistente. Isso causa:

1. **Dados fora de sincronia** — `rental_value` existe em Apartment E Lease, sincronizado via serializers (não signals), quebrando quando dados são alterados fora da API
2. **Campos no model errado** — `contract_generated` está no Apartment mas é do Lease; `deposit_amount` está no Tenant mas é do contrato
3. **Campos mortos** — `Tenant.rent_due_day` nunca é usado (toda lógica usa `Lease.due_day`)
4. **Sync frágil** — serializers fazem `Lease.objects.filter().update()` para sincronizar, bypassando validation e signals

### Nota semântica: `due_day` no Tenant

Mover `due_day` para Tenant significa que `change_due_date` (ação do Lease) agora escreve no Tenant. Consequência: se um inquilino tiver múltiplos leases (histórico), mudar o `due_day` via qualquer lease afeta o registro pessoal do inquilino permanentemente. Isso é correto para o domínio — o dia de vencimento é do inquilino, não do contrato — mas a consequência deve ser explícita.

## Princípio de classificação

**Fonte de verdade = onde o dado persiste quando o contrato muda:**

- Se o inquilino troca de kitnet e o dado se mantém → fonte é o **Tenant** (ex: `due_day`, `warning_count`)
- Se o kitnet troca de inquilino e o dado se mantém → fonte é o **Apartment** (ex: `rental_value`, `cleaning_fee`)
- Se o dado morre quando o contrato acaba → fonte é o **Lease** (ex: `contract_signed`, `interfone_configured`, `deposit_amount`)

## Design: Novo Modelo de Dados

### Building (sem mudanças)

```
Building
├── street_number: PositiveInteger (unique)
├── name: CharField(100)
├── address: CharField(200)
└── [AuditMixin, SoftDeleteMixin]
```

### Apartment — propriedades físicas + financeiras do imóvel

```
Apartment
├── building: FK → Building
├── number: PositiveInteger (unique per building)
├── rental_value: Decimal(10,2)           ← FONTE DE VERDADE
├── cleaning_fee: Decimal(10,2)           ← FONTE DE VERDADE
├── max_tenants: PositiveInteger
├── is_rented: Boolean (default=False)    ← sincronizado via signal de Lease
├── last_rent_increase_date: Date?
├── furnitures: M2M → Furniture
├── owner: FK → Person?
└── [AuditMixin, SoftDeleteMixin]
```

**Campos REMOVIDOS do Apartment:**

| Campo | Motivo | Novo local |
|-------|--------|------------|
| `contract_generated` | Status deste contrato | Lease |
| `contract_signed` | Status deste contrato | Lease |
| `interfone_configured` | Configurado para este inquilino | Lease |
| `lease_date` | Duplicação de `lease.start_date` | Acessar via `apartment.lease.start_date` |

### Tenant — dados pessoais que acompanham o inquilino

```
Tenant
├── user: OneToOne → User?
├── name: CharField(150)
├── cpf_cnpj: CharField(20, unique)
├── is_company: Boolean
├── rg: CharField(20)?
├── phone: CharField(20)
├── marital_status: CharField(50)
├── profession: CharField(100)
├── due_day: PositiveInteger (default=1)  ← RENOMEADO de rent_due_day, FONTE DE VERDADE
├── warning_count: PositiveInteger        ← MOVIDO de Lease
├── furnitures: M2M → Furniture
└── [AuditMixin, SoftDeleteMixin]
```

**Campos REMOVIDOS do Tenant:**

| Campo | Motivo | Novo local |
|-------|--------|------------|
| `deposit_amount` | Caução é do contrato | Lease |
| `cleaning_fee_paid` | Pagamento deste contrato | Lease |
| `tag_deposit_paid` | Pagamento deste contrato | Lease |

**Campos RENOMEADOS no Tenant:**

| Antigo | Novo | Motivo |
|--------|------|--------|
| `rent_due_day` | `due_day` | Clareza, consistência |

**Campos MOVIDOS para Tenant:**

| Campo | Origem | Motivo |
|-------|--------|--------|
| `warning_count` | Lease | Avisos são do inquilino, não do contrato |

### Lease — tudo que é específico DESTE contrato

```
Lease
├── apartment: OneToOne → Apartment
├── responsible_tenant: FK → Tenant
├── tenants: M2M → Tenant
├── number_of_tenants: PositiveInteger
├── start_date: Date
├── validity_months: PositiveInteger
├── tag_fee: Decimal(10,2)
├── deposit_amount: Decimal(10,2)?        ← MOVIDO de Tenant
├── cleaning_fee_paid: Boolean            ← MOVIDO de Tenant
├── tag_deposit_paid: Boolean             ← MOVIDO de Tenant
├── contract_generated: Boolean           ← FONTE DE VERDADE (já existia, remove do Apartment)
├── contract_signed: Boolean              ← FONTE DE VERDADE (já existia, remove do Apartment)
├── interfone_configured: Boolean         ← FONTE DE VERDADE (já existia, remove do Apartment)
├── prepaid_until: Date?
├── is_salary_offset: Boolean
└── [AuditMixin, SoftDeleteMixin]
```

**Campos REMOVIDOS do Lease:**

| Campo | Motivo | Novo local |
|-------|--------|------------|
| `rental_value` | Fonte é o imóvel | Acessar via `lease.apartment.rental_value` |
| `cleaning_fee` | Fonte é o imóvel | Acessar via `lease.apartment.cleaning_fee` |
| `due_day` | Fonte é o inquilino | Acessar via `lease.responsible_tenant.due_day` |
| `warning_count` | Avisos são do inquilino | Tenant |

**Campos MOVIDOS para Lease:**

| Campo | Origem | Motivo |
|-------|--------|--------|
| `deposit_amount` | Tenant | Caução é do contrato, não da pessoa |
| `cleaning_fee_paid` | Tenant | Pagamento relativo a este contrato |
| `tag_deposit_paid` | Tenant | Pagamento relativo a este contrato |

### Furniture e Dependent (sem mudanças)

```
Furniture: name, description, [AuditMixin, SoftDeleteMixin]
Dependent: tenant FK, name, phone, [AuditMixin, SoftDeleteMixin]
```

## Signal: Lease → Apartment.is_rented (NOVO — adicionar a `core/signals.py`)

Único campo derivado mantido no banco (para permitir filtros SQL eficientes). Este signal **não existe** atualmente — deve ser criado.

```python
# Em core/signals.py — NOVO handler

# post_save: Cobre tanto criação quanto soft-delete (SoftDeleteMixin.delete() chama save())
@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender, instance, **kwargs):
    is_rented = not instance.is_deleted
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=is_rented)

# post_delete: Cobre hard delete (caso raro, mas deve ser tratado)
@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender, instance, **kwargs):
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=False)
```

**Nota:** Soft delete no sistema usa `save()` com `is_deleted=True`, disparando `post_save` (não `post_delete`). Ambos os handlers são necessários para cobrir todos os cenários.

## Diagrama de Relacionamentos

```
Building (1) ──── (N) Apartment
                        ├── rental_value, cleaning_fee (FONTE DE VERDADE)
                        ├── is_rented (synced via signal)
                        ├── (M2M) Furniture
                        └── (1:1) Lease
                                    ├── contract_generated/signed
                                    ├── interfone_configured
                                    ├── deposit_amount, cleaning_fee_paid, tag_deposit_paid
                                    ├── (FK) Tenant (responsible)
                                    │         ├── due_day (FONTE DE VERDADE)
                                    │         ├── warning_count
                                    │         └── (M2M) Furniture (pessoal)
                                    └── (M2M) Tenant (todos)
```

## API & Serializers

### Princípio

A API reflete o modelo de domínio. Cada endpoint retorna os campos que são seus. Dados relacionados vêm via nested serializers (read) ou `_id` fields (write). Nenhum campo é projetado de outro model.

### ApartmentSerializer

```json
{
  "id": 1,
  "building": { "id": 1, "street_number": 836, "name": "Prédio 836" },
  "number": 101,
  "rental_value": "1500.00",
  "cleaning_fee": "200.00",
  "max_tenants": 2,
  "is_rented": true,
  "last_rent_increase_date": null,
  "furnitures": [{ "id": 1, "name": "Cama" }],
  "owner": null,
  "lease": {
    "id": 5,
    "contract_generated": true,
    "contract_signed": false,
    "interfone_configured": true,
    "start_date": "2026-01-01",
    "validity_months": 12,
    "responsible_tenant": { "id": 3, "name": "João" }
  }
}
```

- `contract_generated`, `contract_signed`, `interfone_configured` vêm nested via `lease`
- `is_rented` é read-only
- `lease_date` removido (é `lease.start_date`)

### TenantSerializer

```json
{
  "id": 3,
  "name": "João Silva",
  "cpf_cnpj": "12345678901",
  "is_company": false,
  "rg": "123456789",
  "phone": "(11) 99999-9999",
  "marital_status": "Solteiro(a)",
  "profession": "Engenheiro",
  "due_day": 10,
  "warning_count": 0,
  "furnitures": [{ "id": 3, "name": "Sofá" }],
  "dependents": []
}
```

- `rent_due_day` renomeado para `due_day`
- `warning_count` movido de Lease
- `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid` removidos

### LeaseSerializer

```json
{
  "id": 5,
  "apartment": { "id": 1, "number": 101, "rental_value": "1500.00", "cleaning_fee": "200.00" },
  "responsible_tenant": { "id": 3, "name": "João", "due_day": 10 },
  "tenants": [{ "id": 3, "name": "João" }, { "id": 4, "name": "Maria" }],
  "number_of_tenants": 2,
  "start_date": "2026-01-01",
  "validity_months": 12,
  "tag_fee": "80.00",
  "deposit_amount": "1500.00",
  "cleaning_fee_paid": true,
  "tag_deposit_paid": false,
  "contract_generated": true,
  "contract_signed": false,
  "interfone_configured": true,
  "prepaid_until": null,
  "is_salary_offset": false
}
```

- `rental_value`, `cleaning_fee` vêm nested via `apartment`
- `due_day` vem nested via `responsible_tenant`
- `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid` agora são campos próprios

## Fluxo de edição cross-model

**Princípio:** Cada campo é editado no endpoint do seu model dono. O frontend faz a chamada correta e invalida os caches afetados.

### Editar `rental_value` (de qualquer página)

```
Frontend → PATCH /api/apartments/{id}/ { rental_value: "1600.00" }
         → invalida ['apartments'], ['leases'], ['dashboard']
```

### Editar `due_day` (de qualquer página)

```
Frontend → PATCH /api/tenants/{id}/ { due_day: 15 }
         → invalida ['tenants'], ['leases']
```

### Editar campos do Lease (de qualquer página)

```
Frontend → PATCH /api/leases/{id}/ { deposit_amount: "2000.00", contract_signed: true }
         → invalida ['leases'], ['apartments'], ['dashboard']
```

### Form do Lease com campos de múltiplos models

```typescript
const onSubmit = async (data: LeaseFormData) => {
  // 1. Campos do Apartment (se mudaram)
  if (apartmentFieldsChanged) {
    await updateApartment({ id: lease.apartment.id, rental_value, cleaning_fee });
  }

  // 2. Campos do Tenant (se mudaram)
  if (tenantFieldsChanged) {
    await updateTenant({ id: lease.responsible_tenant.id, due_day });
  }

  // 3. Campos do Lease
  await updateLease({ id: lease.id, ...leaseFields });
};
```

## Cache Invalidation (TanStack Query)

```
Mutation em Apartment → invalida ['apartments'], ['leases'], ['dashboard']
Mutation em Lease     → invalida ['leases'], ['apartments'], ['dashboard']
Mutation em Tenant    → invalida ['tenants'], ['leases']
Mutation em Furniture → invalida ['furniture'], ['apartments'], ['tenants'], ['leases']
```

## Impacto em Views (endpoints)

### `change_due_date` action (`core/views.py`)

Hoje escreve `lease.due_day` e chama `calculate_due_date_change_fee` com `lease.rental_value` e `lease.due_day`. Após refactor:

```python
# ANTES
fee = FeeCalculatorService.calculate_due_date_change_fee(
    rental_value=lease.rental_value,
    current_due_day=lease.due_day,
    new_due_day=new_due_day,
)
lease.due_day = new_due_day
lease.save()

# DEPOIS
fee = FeeCalculatorService.calculate_due_date_change_fee(
    rental_value=lease.apartment.rental_value,
    current_due_day=lease.responsible_tenant.due_day,
    new_due_day=new_due_day,
)
tenant = lease.responsible_tenant
tenant.due_day = new_due_day
tenant.save(update_fields=['due_day'])
```

### `calculate_late_fee` action (`core/views.py`)

Hoje lê `lease.rental_value` e `lease.due_day`. Após refactor:

```python
# ANTES
FeeCalculatorService.calculate_late_fee(
    rental_value=lease.rental_value, due_day=lease.due_day, ...
)

# DEPOIS
FeeCalculatorService.calculate_late_fee(
    rental_value=lease.apartment.rental_value,
    due_day=lease.responsible_tenant.due_day, ...
)
```

## Impacto em Services

### contract_service.py — Geração de PDF

```python
# ANTES                          # DEPOIS
lease.rental_value            →  lease.apartment.rental_value
lease.cleaning_fee            →  lease.apartment.cleaning_fee
lease.due_day                 →  lease.responsible_tenant.due_day
```

**ATENÇÃO:** O `select_related('apartment', 'responsible_tenant')` existe no `get_queryset()` do LeaseViewSet (aplica-se a `list`/`retrieve`), mas ações custom como `generate_contract` usam `self.get_object()` que pode não incluir o `select_related`. O `get_object()` do `generate_contract` deve ser atualizado para garantir que `apartment` e `responsible_tenant` estejam carregados, evitando N+1 queries.

### fee_calculator.py — Multa por atraso

```python
# ANTES
late_fee = 0.05 * (lease.rental_value / 30) * days_late

# DEPOIS
late_fee = 0.05 * (lease.apartment.rental_value / 30) * days_late
```

### daily_control_service.py — Controle diário

Referencia `lease.due_day` e `lease.rental_value` em múltiplos pontos. Substituir:

```python
lease.rental_value  →  lease.apartment.rental_value
lease.cleaning_fee  →  lease.apartment.cleaning_fee
lease.due_day       →  lease.responsible_tenant.due_day
```

### simulation_service.py — Simulações financeiras

Usa `apartment.lease.rental_value` (acesso reverso). Após refactor, `rental_value` fica no Apartment:

```python
# ANTES
apartment.lease.rental_value

# DEPOIS (simplifica — dado já está no apartment)
apartment.rental_value
```

### cash_flow_service.py — Fluxo de caixa

Tem 8+ acessos a `lease.rental_value` e acessos a `lease.due_day`. Substituir todos:

```python
lease.rental_value  →  lease.apartment.rental_value
lease.cleaning_fee  →  lease.apartment.cleaning_fee
lease.due_day       →  lease.responsible_tenant.due_day
```

Verificar que todas as queries que carregam leases neste service usam `select_related('apartment', 'responsible_tenant')`.

### dashboard_service.py

Mesmas substituições de `lease.rental_value` → `lease.apartment.rental_value` e `lease.due_day` → `lease.responsible_tenant.due_day`. Queries com `select_related` já cobrem os joins.

### Furniture no contrato (sem mudança)

`apartment.furnitures - tenant.furnitures` permanece igual.

## Impacto em Serializers (outros)

### PersonIncomeSerializer (`core/serializers.py`)

`get_current_value` lê `lease.rental_value`. Atualizar para `lease.apartment.rental_value`.

### RentPaymentSerializer (`core/serializers.py`)

Embeds `LeaseSerializer` que não terá mais `rental_value`/`due_day` como campos top-level. Consumidores do endpoint de rent-payments devem acessar via `rent_payment.lease.apartment.rental_value`.

## Impacto em Validators

### `validate_due_day` validator

Atualmente em `Lease.due_day` com `validators=[validate_due_day]`. O campo `Tenant.rent_due_day` **NÃO tem** esse validator. Após o `RenameField`, o campo `Tenant.due_day` continuará sem validator. É necessário um `AlterField` na migração 0018 (após o `RenameField`) para adicionar `validators=[validate_due_day]` ao campo `Tenant.due_day`. Sem isso, valores inválidos (0, 32+) serão aceitos silenciosamente.

### `validate_lease_dates` validator

Em `Lease.clean()`. Verificar se acessa `self.due_day` internamente — se sim, atualizar para `self.responsible_tenant.due_day`.

## Impacto em Contract Template

### Template Jinja2 (`contract-template/page.tsx`)

Template usa `tenant.deposit_amount` na geração do contrato. Após refactor:

```
# ANTES
{% if tenant.deposit_amount and tenant.deposit_amount > 0 %}

# DEPOIS
{% if lease.deposit_amount and lease.deposit_amount > 0 %}
```

O namespace do template de contrato precisa ser atualizado em `contract_service.py` (contexto passado ao template).

## Estratégia de Migração

### 3 migrações sequenciais

**Migração 0017: Adicionar novos campos**

```python
# Tenant: campo vindo de Lease
AddField('tenant', 'warning_count', PositiveIntegerField(default=0))

# Lease: campos vindos de Tenant
AddField('lease', 'deposit_amount', DecimalField(max_digits=10, decimal_places=2, null=True))
AddField('lease', 'cleaning_fee_paid', BooleanField(default=False))
AddField('lease', 'tag_deposit_paid', BooleanField(default=False))
```

**Migração 0018: Data migration + rename**

**IMPORTANTE:** Dentro de data migrations, `apps.get_model()` retorna manager padrão (sem `SoftDeleteManager`). Usar `.filter(is_deleted=False)` explicitamente quando necessário. O `RenameField` vem DEPOIS do `RunPython` — durante o `RunPython`, o campo ainda se chama `rent_due_day` (nome antigo).

```python
def migrate_data(apps, schema_editor):
    Lease = apps.get_model('core', 'Lease')
    Apartment = apps.get_model('core', 'Apartment')

    # Lease → Tenant: warning_count
    # NOTA: Usa ALL leases (incluindo soft-deleted) com aggregation para não perder dados.
    # Se tenant tem múltiplos leases históricos, usa o MAX (acumula avisos).
    from django.db.models import Max
    Tenant = apps.get_model('core', 'Tenant')
    tenant_warnings = (
        Lease.objects.values('responsible_tenant_id')
        .annotate(max_warnings=Max('warning_count'))
    )
    for entry in tenant_warnings:
        Tenant.objects.filter(pk=entry['responsible_tenant_id']).update(
            warning_count=entry['max_warnings']
        )

    # Tenant → Lease: deposit_amount, cleaning_fee_paid, tag_deposit_paid
    # Copia do responsible_tenant para cada lease (incluindo soft-deleted)
    for lease in Lease.objects.select_related('responsible_tenant').all():
        tenant = lease.responsible_tenant
        lease.deposit_amount = tenant.deposit_amount
        lease.cleaning_fee_paid = tenant.cleaning_fee_paid
        lease.tag_deposit_paid = tenant.tag_deposit_paid
        lease.save(update_fields=['deposit_amount', 'cleaning_fee_paid', 'tag_deposit_paid'])

    # Sync is_rented (só leases ativos)
    Apartment.objects.update(is_rented=False)
    for lease in Lease.objects.filter(is_deleted=False).select_related('apartment'):
        Apartment.objects.filter(pk=lease.apartment_id).update(is_rented=True)

# Operações na migração (ordem importa):
# 1. RunPython(migrate_data, reverse_migrate_data)  ← usa nome antigo rent_due_day
# 2. RenameField('tenant', 'rent_due_day', 'due_day')  ← renomeia após data migration
# 3. AlterField('tenant', 'due_day', validators=[validate_due_day])  ← adiciona validator que não existia
```

**Migração 0019: Remover campos antigos + índices**

```python
# Remover índice que referencia Lease.due_day (antes de remover o campo)
RemoveIndex('lease', name='lease_due_date_idx')

# Apartment
RemoveField('apartment', 'contract_generated')
RemoveField('apartment', 'contract_signed')
RemoveField('apartment', 'interfone_configured')
RemoveField('apartment', 'lease_date')

# Lease
RemoveField('lease', 'rental_value')
RemoveField('lease', 'cleaning_fee')
RemoveField('lease', 'due_day')
RemoveField('lease', 'warning_count')

# Tenant
RemoveField('tenant', 'deposit_amount')
RemoveField('tenant', 'cleaning_fee_paid')
RemoveField('tenant', 'tag_deposit_paid')
```

### Segurança

1. Backup do banco ANTES de rodar migrações
2. Migrações 0017 e 0018 são reversíveis
3. Migração 0019 é destrutiva — só executar após validação
4. Script de validação pós-migração verifica integridade

## Frontend — Mudanças por página

### Apartments (`/apartments`)

- Tabela: remove colunas `contract_generated`, `contract_signed`, `interfone_configured` (mostrar via `apartment.lease?.contract_generated` se desejado)
- Remove `lease_date` (mostrar `apartment.lease?.start_date`)
- Form: remove campos do lease — editáveis só via `/leases`
- `is_rented` vira badge read-only

### Leases (`/leases`)

- Tabela: `rental_value` vem de `lease.apartment.rental_value`, `due_day` de `lease.responsible_tenant.due_day`
- Form: `rental_value`/`cleaning_fee` salvam via `PATCH /api/apartments/`, `due_day` via `PATCH /api/tenants/`, demais via `PATCH /api/leases/`
- Adiciona `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid` ao form

### Tenants (`/tenants`)

- Tabela: adiciona `due_day`, `warning_count`
- Form: `due_day` e `warning_count` editáveis; remove `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`
- **Wizard** (`tenants/_components/wizard/`): atualizar payload — remove `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`; renomeia `rent_due_day` → `due_day`

### Schemas (Zod)

- `apartment.schema.ts`: remove `contract_generated`, `contract_signed`, `interfone_configured`, `lease_date`; adiciona nested `lease` opcional
- `lease.schema.ts`: remove `rental_value`, `cleaning_fee`, `due_day`, `warning_count`; adiciona `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`
- `tenant.schema.ts`: renomeia `rent_due_day` → `due_day`; adiciona `warning_count`; remove `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`

### Tipos locais em componentes

- `dependent-form-list.tsx`: tem tipo local `TenantFormData` com campos removidos — atualizar para refletir novo schema

## Impacto em Scripts

### `scripts/import_financial_data.py`

Verificar se referencia `Lease.due_day`, `Tenant.rent_due_day`, `Tenant.deposit_amount`, etc. Atualizar campo names para novo modelo.

### `scripts/data/financial_data_template.json`

Atualizar estrutura se contém campos que mudaram de model.

## Testes impactados

- **Unit tests de services**: atualizar caminhos (`lease.rental_value` → `lease.apartment.rental_value`)
- **Integration tests de serializers**: atualizar payloads (campos movidos entre models)
- **Integration tests de views**: atualizar `change_due_date` e `calculate_late_fee` tests
- **Frontend tests de hooks**: atualizar MSW handlers para nova estrutura de response
- **Testes de contrato PDF**: atualizar fixtures e template context

## Checklist de auditoria pós-refactor

Grep completo no codebase para garantir que nenhuma referência aos campos antigos restou:

```bash
# Backend — campos removidos do Lease
rg "lease\.(rental_value|cleaning_fee|due_day|warning_count)" core/ tests/

# Backend — campos removidos do Apartment
rg "apartment\.(contract_generated|contract_signed|interfone_configured|lease_date)" core/ tests/

# Backend — campos removidos do Tenant
rg "tenant\.(deposit_amount|cleaning_fee_paid|tag_deposit_paid|rent_due_day)" core/ tests/

# Frontend — campos antigos
rg "(rent_due_day|lease_date)" frontend/

# Frontend — acessos diretos a campos movidos
rg "lease\.(rental_value|cleaning_fee|due_day)" frontend/
```
