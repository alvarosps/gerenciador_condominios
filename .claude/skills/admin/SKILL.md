---
name: admin
description: Use when implementing property administration logic — buildings, apartments, tenants, leases, contracts, furniture, late fees, tag fees, due dates, or any CRUD related to the core property management domain.
argument-hint: "[what-to-implement]"
---

# Property Administration Implementation Guide

Current branch: !`git branch --show-current`
Recent migrations: !`ls -1 core/migrations/0*.py | tail -3`

## Domain Knowledge — CRITICAL

### Data Model

```
Building (street_number unique)
    → Apartment (number unique per building)
        → Lease (OneToOne with Apartment)
            → responsible_tenant (FK Tenant)
            → tenants (M2M via LeaseTenant, db_table='core_lease_tenant_details')
Tenant (cpf_cnpj unique)
    → Dependent (FK)
Furniture ↔ Apartment (M2M)
Furniture ↔ Tenant (M2M)
```

### Business Rules

| Rule | Logic | Location |
|------|-------|----------|
| Tag fee | R$50 for 1 tenant, R$80 for 2+ (based on `Lease.number_of_tenants`) | `fee_calculator.py` |
| Late fee | 5% daily × (rental_value ÷ 30) × days_late | `fee_calculator.py` |
| Contract furniture | Apartment furniture − Tenant furniture | `contract_service.py` |
| PDF path | `contracts/{building_number}/contract_apto_{apt_number}_{lease_id}.pdf` | `contract_service.py` |
| Soft delete | All models use `SoftDeleteMixin` — `Model.objects.all()` excludes deleted | `models.py` |
| Audit trail | All models use `AuditMixin` — auto-tracks created/updated at/by | `models.py` |

### Lease Lifecycle

1. Create lease with apartment + responsible tenant + tenants (M2M)
2. Tag fee auto-calculated based on `number_of_tenants`
3. Generate contract PDF: `POST /api/leases/{id}/generate_contract/`
4. Contract uses Landlord data, ContractRules, and template from `core/templates/`
5. Change due date: `POST /api/leases/{id}/change_due_date/`
6. Calculate late fee: `POST /api/leases/{id}/calculate_late_fee/`

### Brazilian Validation

| Field | Rule |
|-------|------|
| CPF | 11 digits + checksum validation (`core/validators/brazilian.py`) |
| CNPJ | 14 digits + checksum validation |
| Phone | (XX) XXXXX-XXXX format |
| Currency | R$ 1.500,00 |
| Date | DD/MM/YYYY |
| Marital status | Solteiro(a), Casado(a), Divorciado(a), Viúvo(a), União Estável |

### Landlord (Singleton)

- `Landlord.get_active()` returns the active landlord
- Only one landlord can be active at a time (`is_active=True`)
- Used in contract generation for owner details

### Contract Rules

- `ContractRule.get_active_rules()` returns ordered active rules
- Rules are HTML content with `order` field for sorting
- Templates use Jinja2 with variables like `{{ tenant_name }}`, `{{ apartment_number }}`

## Services Architecture

| Service | Responsibility |
|---------|---------------|
| `ContractService` | PDF generation via Pyppeteer + Jinja2 |
| `FeeCalculatorService` | Tag fee and late fee calculations |
| `DateCalculatorService` | Due date logic, lease expiration, rent increase dates |
| `TemplateManagementService` | Template save, restore, backup versioning |
| `DashboardService` | Financial summary, lease metrics, tenant/building stats |
| `BaseService[T]` | Generic CRUD operations (get, create, update, delete) |

## Cache Layer

- `CacheManager` + `@cache_result` decorator in `core/cache.py`
- Automatic invalidation via Django signals in `core/signals.py`
- When adding new models: add signal handlers for cache invalidation
- `CacheManager.invalidate_model(name, pk)` and `invalidate_pattern(pattern)`

## ViewSet Patterns

- Use `ModelViewSet` for standard CRUD
- Custom actions: `@action(detail=True)` for instance, `@action(detail=False)` for collection
- Query optimization: `select_related()` for FK, `prefetch_related()` for M2M
- Filters via query params: `?building_id=1&is_rented=true`

## Serializer Dual Pattern

```python
# Read — nested objects
building = BuildingSerializer(read_only=True)
# Write — IDs
building_id = PrimaryKeyRelatedField(source='building', write_only=True)
# M2M write — _ids suffix
furniture_ids = PrimaryKeyRelatedField(many=True, source='furnitures', write_only=True)
```

## Frontend Patterns

- CRUD pages use `useCrudPage` hook
- Tenant form: 6-step wizard in `tenants/_components/wizard/`
- Table columns defined with Ant Design `Column<T>[]`
- Export: `/export/excel/` and `/export/csv/` on each resource
- Error handling: `getErrorMessage()` and `handleError()`
