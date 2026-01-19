# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Condomínios Manager is a comprehensive property management system for rental properties in Brazil. The system manages buildings, apartments, tenants, leases, and furniture inventory with full contract generation capabilities.

**Project Status:**
- Backend: 100% complete (Django REST Framework)
- Frontend: 100% complete (Next.js 14 + React 18)
- Testing: Comprehensive test suite with 600+ tests (523 backend + 93 frontend)
- Coverage: 83.86% backend code coverage

## Tech Stack

### Backend
- **Framework**: Django 5.2+, Django REST Framework 3.14.0
- **Database**: PostgreSQL 15+
- **Authentication**: JWT (SimpleJWT) + Google OAuth2 (django-allauth)
- **PDF Generation**: Pyppeteer (Chrome headless)
- **Key Libraries**:
  - `num2words` - Currency in Portuguese words
  - `Pillow` - Image handling
  - `python-dateutil` - Date calculations
  - `django-cors-headers` - CORS support

### Frontend
- **Framework**: Next.js 14.2.18 (App Router)
- **UI**: React 18 + Ant Design 5 + Tailwind CSS
- **State Management**:
  - Zustand (client state, auth)
  - TanStack Query v5 (server state)
- **Forms**: React Hook Form + Zod validation
- **HTTP Client**: Axios with interceptors
- **Code Editor**: Monaco Editor (contract template)
- **Testing**: Vitest + React Testing Library + MSW

---

## Architecture

### Data Model Hierarchy

```
Building (Prédio)
├── street_number (unique)
├── street, city, state, zip_code
├── common_water_bill, common_energy_bill
└── apartments[]

Apartment (Apartamento)
├── building_id (FK)
├── number (unique per building)
├── bedrooms, floor_number, is_front
├── furnitures[] (M2M)
└── lease (OneToOne)

Lease (Locação)
├── apartment_id (OneToOne)
├── responsible_tenant_id (FK)
├── tenants[] (M2M via LeaseTenant)
├── start_date, validity_months, due_day
├── rental_value, cleaning_fee, tag_fee
└── status: active/expired/terminated

Tenant (Inquilino)
├── name, cpf_cnpj (unique), phone
├── email, marital_status, profession
├── is_company (boolean)
├── user_id (FK to Django User, optional)
├── furnitures[] (M2M)
└── dependents[]

Dependent (Dependente)
├── tenant_id (FK)
├── name, phone
└── relationship (optional)

Furniture (Móvel)
├── name, description
├── condition (new/good/fair/poor)
└── apartments[] and tenants[] (M2M)
```

### Model Mixins

All models include `AuditMixin` and `SoftDeleteMixin`:

**AuditMixin** - Automatic tracking of record history:
- `created_at` - Timestamp when record was created
- `updated_at` - Timestamp of last modification (auto-updated)
- `created_by` - User who created the record
- `updated_by` - User who last modified the record

**SoftDeleteMixin** - Safe deletion with recovery:
- `is_deleted` - Boolean flag (indexed for performance)
- `deleted_at` - Timestamp of deletion
- `deleted_by` - User who deleted the record

**Query Methods**:
```python
# Default queryset excludes deleted records
Building.objects.all()  # Only non-deleted

# Include deleted records
Building.objects.with_deleted()

# Only deleted records
Building.objects.deleted_only()

# Soft delete a record
building.delete(deleted_by=user)  # Sets is_deleted=True

# Permanently delete
building.delete(hard_delete=True)

# Restore a soft-deleted record
building.restore(restored_by=user)
```

### Service Layer Architecture

The backend uses a service layer pattern:

```
core/services/
├── contract_service.py      # PDF generation, HTML rendering
├── dashboard_service.py     # Analytics, metrics, statistics
├── template_management_service.py  # Contract template CRUD
├── fee_calculator.py        # Late fees, due date changes
└── date_calculator.py       # Date arithmetic, leap years
```

### Viewsets Architecture

Views are organized in both main views.py and specialized viewsets:

```
core/
├── views.py                 # Main viewsets (Building, Apartment, Tenant, Lease, etc.)
└── viewsets/
    ├── __init__.py
    └── template_views.py    # ContractTemplateViewSet (separated for clarity)
```

### Frontend Architecture

```
frontend/
├── app/(dashboard)/         # Protected routes (App Router)
│   ├── page.tsx            # Dashboard with 5 widgets
│   ├── buildings/          # Building CRUD
│   ├── apartments/         # Apartment CRUD
│   ├── tenants/            # Tenant CRUD with wizard
│   │   └── _components/
│   │       └── wizard/     # Step-based wizard components
│   ├── leases/             # Lease CRUD + contract actions
│   │   └── _components/    # Lease-specific components
│   ├── furniture/          # Furniture CRUD
│   └── contract-template/  # Monaco editor page
├── app/login/              # Auth page
├── components/
│   ├── layouts/            # MainLayout, Sidebar, Header, MobileNav
│   ├── shared/             # ConfirmDialog, DeleteConfirmDialog, Loading
│   ├── tables/             # DataTable with Ant Design
│   ├── ui/                 # Shadcn/ui components (sheet, skeleton, etc.)
│   └── search/             # GlobalSearch component
├── lib/
│   ├── api/
│   │   ├── client.ts       # Axios instance with interceptors
│   │   └── hooks/          # TanStack Query hooks
│   ├── schemas/            # Zod validation schemas
│   ├── hooks/              # Custom React hooks
│   │   ├── use-crud-page.ts    # CRUD page state management
│   │   ├── use-hydration.ts    # SSR hydration utility
│   │   └── use-export.ts       # Export functionality
│   └── utils/
│       ├── validators.ts   # CPF/CNPJ validation
│       ├── formatters.ts   # Currency, date formatting
│       └── error-handler.ts # Error handling utilities
└── store/
    └── auth-store.ts       # Zustand auth state
```

### Tenant Wizard Architecture

The tenant form uses a step-based wizard pattern:

```
frontend/app/(dashboard)/tenants/_components/wizard/
├── index.tsx              # Main wizard coordinator
├── types.ts               # Shared TypeScript types
├── basic-info-step.tsx    # Step 1: Name, CPF/CNPJ, Company flag
├── contact-info-step.tsx  # Step 2: Phone, Email, Address
├── professional-info-step.tsx # Step 3: Profession, Marital Status
├── dependents-step.tsx    # Step 4: Add/edit dependents
├── furniture-step.tsx     # Step 5: Assign furniture
└── review-step.tsx        # Step 6: Review all data
```

---

## API Reference

### Base URL: `/api/`

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/token/` | Login, returns access + refresh tokens |
| POST | `/api/token/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Get current user info |
| POST | `/api/auth/logout/` | Logout (blacklist token) |
| GET | `/api/auth/google/` | Google OAuth redirect |
| GET | `/api/auth/google/callback/` | Google OAuth callback |

### CRUD Endpoints (all resources)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/{resource}/` | List all (paginated) |
| POST | `/api/{resource}/` | Create new |
| GET | `/api/{resource}/{id}/` | Get by ID |
| PUT | `/api/{resource}/{id}/` | Full update |
| PATCH | `/api/{resource}/{id}/` | Partial update |
| DELETE | `/api/{resource}/{id}/` | Delete |

Resources: `buildings`, `apartments`, `tenants`, `leases`, `furnitures`, `dependents`

### Special Lease Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/leases/{id}/generate_contract/` | Generate PDF contract |
| GET | `/api/leases/{id}/calculate_late_fee/` | Calculate late payment fees |
| POST | `/api/leases/{id}/change_due_date/` | Change due date with fee |

### Contract Template Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates/current/` | Get current template HTML |
| POST | `/api/templates/save/` | Save template (auto-backup) |
| GET | `/api/templates/backups/` | List all template backups |
| POST | `/api/templates/restore/` | Restore from backup |
| POST | `/api/templates/preview/` | Preview with sample data |

**Note**: Template backups are stored in `core/templates/backups/` with timestamped filenames.

### Dashboard Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/financial_summary/` | Financial summary |
| GET | `/api/dashboard/late_payment_summary/` | Late payment list |
| GET | `/api/dashboard/lease_metrics/` | Expiring leases, occupancy |
| GET | `/api/dashboard/tenant_statistics/` | Tenant demographics |
| GET | `/api/dashboard/building_statistics/` | Per-building analytics |

### Export Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/{resource}/export/excel/` | Export to Excel |
| GET | `/api/{resource}/export/csv/` | Export to CSV |

---

## Business Logic

### Contract Generation
- **Location**: `core/services/contract_service.py`
- Uses Jinja2 template + Pyppeteer (Chrome headless) for PDF
- Furniture in contract = Apartment furniture - Tenant furniture
- Tag fee: R$50 for 1 tenant, R$80 for 2+ tenants
- PDFs saved to: `contracts/{building_number}/contract_apto_{apt_number}_{lease_id}.pdf`

### Fee Calculations
- **Location**: `core/services/fee_calculator.py`
- Late fee: 5% per day × (rental_value ÷ 30) × days_late
- Due date change fee: (rental_value ÷ 30) × days_difference

### Date Calculations
- **Location**: `core/services/date_calculator.py`
- Handles leap year edge cases (Feb 29 → Feb 28 → March 1)
- Final date: start_date + validity_months

### Brazilian Validation
- **CPF**: 11 digits with checksum validation
- **CNPJ**: 14 digits with checksum validation
- **Marital Status Options**: Solteiro(a), Casado(a), Divorciado(a), Viúvo(a), União Estável
- **Currency Format**: R$ 1.500,00 (Brazilian Real)
- **Date Format**: DD/MM/YYYY

---

## Middleware & Logging

### Request/Response Logging
**Location**: `core/middleware/logging_middleware.py`

The `RequestResponseLoggingMiddleware` provides comprehensive logging:

**Access Logger** (`access`):
- Request method, path, user, IP address
- User agent, content type
- Response status code, duration (ms)

**Performance Logger** (`performance`):
- Logs warnings for slow requests (> 1 second)
- Format: `SLOW_REQUEST: {method} {path} took {duration}ms`

**IP Detection**: Supports proxy headers (`X-Forwarded-For`) for accurate client IP tracking.

---

## Frontend Utilities

### Error Handler (`lib/utils/error-handler.ts`)

**Type Guards**:
- `isAxiosError(error)` - Check if error is AxiosError
- `isNetworkError(error)` - No response from server
- `isAuthError(error)` - 401 status
- `isValidationError(error)` - 400 status
- `isForbiddenError(error)` - 403 status
- `isNotFoundError(error)` - 404 status
- `isServerError(error)` - 5xx status

**Functions**:
```typescript
// Extract user-friendly error message
const message = getErrorMessage(error, 'Fallback message');

// Log error with context
handleError(error, 'CreateBuilding');
```

Supports DRF error formats: `error`, `message`, `detail`, `non_field_errors`.

### CRUD Page Hook (`lib/hooks/use-crud-page.ts`)

Consolidates common CRUD page state:

```typescript
const crud = useCrudPage<Building>({
  entityName: 'prédio',
  entityNamePlural: 'prédios',
  deleteMutation,
  exportColumns: columns,
  exportFilename: 'predios',
});

// Use in component
<Button onClick={crud.openCreateModal}>Novo</Button>
<Button onClick={() => crud.openEditModal(item)}>Editar</Button>
<Button onClick={() => crud.handleDeleteClick(item.id)}>Excluir</Button>
```

**Provided State**:
- Modal management: `isModalOpen`, `editingItem`, `openCreateModal()`, `openEditModal()`, `closeModal()`
- Delete dialog: `deleteDialogOpen`, `handleDelete()`, `isDeleting`
- Bulk operations: `bulkDeleteDialogOpen`, `handleBulkDelete()`, `isBulkDeleting`
- Export: `isExporting`, `handleExport(format, data)`

---

## Development Commands

### Backend

```bash
# Setup
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing

# Database (PostgreSQL required)
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver  # http://localhost:8000

# Testing
pytest                           # Run all tests
pytest tests/unit/               # Unit tests only
pytest tests/integration/        # Integration tests only
pytest --cov=core --cov-report=html  # With coverage

# Linting (enforced by pre-commit)
flake8 core/
black core/ --check
isort core/ --check
```

### Frontend

```bash
cd frontend

# Setup
npm install

# Development
npm run dev  # http://localhost:4000

# Build
npm run build
npm run start

# Testing
npm run test           # Run all tests
npm run test:watch     # Watch mode
npm run test:coverage  # With coverage

# Linting
npm run lint           # ESLint
npm run type-check     # TypeScript
npm run format         # Prettier
```

### Docker

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### Database Backup/Restore

```bash
# Create backup
python scripts/backup_db.py
# Output: backups/backup_{db_name}_{timestamp}.backup

# Restore backup
python scripts/restore_db.py backups/backup_condominio_20250112.backup
```

---

## Pre-commit Hooks

The project uses pre-commit for code quality enforcement.

**Configuration**: `.pre-commit-config.yaml`

**Hooks**:
- **Black**: Python formatting (120 char line length)
- **isort**: Import sorting (black profile)
- **flake8**: Python linting (max line 120, ignore E203, W503)
- **General checks**: trailing whitespace, YAML/JSON validation, large file detection, merge conflict markers

**Setup**:
```bash
pip install pre-commit
pre-commit install
```

**Manual Run**:
```bash
pre-commit run --all-files
```

---

## Configuration

### Environment Variables

**Backend (.env)**
```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/condominio
ALLOWED_HOSTS=localhost,127.0.0.1

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Frontend (.env.local)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Database

PostgreSQL configuration in `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'condominio',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### CORS Configuration

Frontend allowed origins in `settings.py`:
- `http://localhost:4000` (Next.js frontend)
- `http://localhost:6000` (Alternative)

---

## Testing

### Backend Tests

Located in `tests/`:
```
tests/
├── unit/
│   ├── test_auth/
│   ├── test_infrastructure/
│   ├── test_services/
│   │   ├── test_contract_service.py
│   │   ├── test_dashboard_service.py
│   │   ├── test_fee_calculator.py
│   │   ├── test_date_calculator.py
│   │   └── test_template_management_service.py
│   ├── test_validators/
│   ├── test_models.py
│   ├── test_serializers.py
│   └── test_utils.py
├── integration/
│   ├── test_api_views.py
│   └── test_template_endpoints.py
└── e2e/
    ├── test_auth_flow.py
    ├── test_lease_workflow.py
    └── test_property_management_flow.py
```

**Test Configuration**: `pytest.ini`
- Uses `pytest-django`
- Reuses database for speed (`--reuse-db`)
- Coverage threshold: 60%

### Frontend Tests

Located in `frontend/lib/api/hooks/__tests__/`:
- `use-auth.test.tsx`
- `use-buildings.test.tsx`
- `use-apartments.test.tsx`
- `use-tenants.test.tsx`
- `use-leases.test.tsx`
- `use-furniture.test.tsx`
- `use-dashboard.test.tsx`
- `use-contract-template.test.tsx`

**Test Configuration**: `vitest.config.mts`
- Uses `@testing-library/react`
- MSW for API mocking
- jsdom environment

### MSW Testing Infrastructure

Mock Service Worker setup for frontend testing:

```
frontend/tests/
├── mocks/
│   ├── handlers.ts      # MSW request handlers
│   ├── server.ts        # MSW server setup
│   ├── index.ts         # Exports
│   └── data/            # Mock data generators
│       ├── buildings.ts
│       ├── apartments.ts
│       ├── tenants.ts
│       ├── leases.ts
│       ├── furniture.ts
│       └── index.ts
├── setup.ts             # Test setup with MSW
└── test-utils.tsx       # Custom render with providers
```

**Usage in Tests**:
```typescript
import { server } from '@/tests/mocks/server';
import { rest } from 'msw';

// Override handler for specific test
server.use(
  rest.get('/api/buildings/', (req, res, ctx) => {
    return res(ctx.json({ results: [] }));
  })
);
```

---

## Frontend Features

### Dashboard (5 Widgets)
1. **Financial Summary**: Total revenue, average rent, late fees collected
2. **Late Payments**: List of overdue leases with days late and amount
3. **Lease Metrics**: Expiring leases (30/60/90 days), occupancy rate
4. **Tenant Statistics**: Marital status distribution, profession breakdown
5. **Building Statistics**: Per-building revenue, occupancy, tenant count

### CRUD Pages
All pages use the `useCrudPage` hook for consistent behavior:
- **Buildings**: Basic CRUD with address management
- **Apartments**: Filter by building, manage furniture
- **Tenants**: Multi-step wizard (6 steps)
- **Leases**: Contract generation, late fees, due date changes
- **Furniture**: Condition tracking, apartment/tenant assignment

### New Components
- **MobileNav** (`components/layouts/mobile-nav.tsx`): Responsive hamburger menu with Sheet
- **DeleteConfirmDialog** (`components/shared/delete-confirm-dialog.tsx`): Reusable delete confirmation
- **Sheet** (`components/ui/sheet.tsx`): Slide-out panel component
- **Skeleton** (`components/ui/skeleton.tsx`): Loading placeholder

### Contract Template Editor
- Monaco Editor with HTML syntax highlighting
- Live preview with sample data
- Automatic backup on save
- Restore from backup functionality
- Available placeholders documentation

### Authentication
- JWT-based with access/refresh tokens
- Google OAuth integration
- Protected routes via middleware
- Persistent auth state (Zustand + localStorage)

---

## Common Patterns

### Creating a Lease (API)
```json
POST /api/leases/
{
  "apartment_id": 1,
  "responsible_tenant_id": 1,
  "tenant_ids": [1, 2],
  "start_date": "2025-01-15",
  "validity_months": 12,
  "due_day": 10,
  "rental_value": "1500.00",
  "cleaning_fee": "200.00",
  "tag_fee": "80.00"
}
```

### Creating a Tenant with Dependents (API)
```json
POST /api/tenants/
{
  "name": "João Silva",
  "cpf_cnpj": "529.982.247-25",
  "phone": "(11) 98765-4321",
  "marital_status": "Casado(a)",
  "profession": "Engenheiro",
  "furniture_ids": [1, 2, 3],
  "dependents": [
    {"name": "Maria Silva", "phone": "(11) 91234-5678"}
  ]
}
```

### Using Frontend Hooks
```typescript
// Buildings CRUD
const { data, isLoading, error } = useBuildings();
const createMutation = useCreateBuilding();
const updateMutation = useUpdateBuilding();
const deleteMutation = useDeleteBuilding();

// Dashboard
const { data: summary } = useDashboardSummary();
const { data: latePayments } = useLatePayments();

// CRUD Page State
const crud = useCrudPage<Building>({
  entityName: 'prédio',
  entityNamePlural: 'prédios',
  deleteMutation,
});
```

### Serializer Pattern (Backend)
```python
# Foreign keys: read with nested, write with _id
building = BuildingSerializer(read_only=True)
building_id = serializers.PrimaryKeyRelatedField(
    queryset=Building.objects.all(),
    source='building',
    write_only=True
)

# Many-to-many: read with nested, write with _ids
furnitures = FurnitureSerializer(many=True, read_only=True)
furniture_ids = serializers.PrimaryKeyRelatedField(
    queryset=Furniture.objects.all(),
    many=True,
    source='furnitures',
    write_only=True
)
```

---

## File Structure

```
condominios_manager/
├── core/                          # Main Django app
│   ├── models.py                  # Data models with mixins
│   ├── serializers.py             # DRF serializers
│   ├── views.py                   # Main API viewsets
│   ├── viewsets/                  # Specialized viewsets
│   │   └── template_views.py      # Contract template viewset
│   ├── urls.py                    # API routing
│   ├── admin.py                   # Django admin config
│   ├── services/                  # Business logic layer
│   │   ├── contract_service.py
│   │   ├── dashboard_service.py
│   │   ├── template_management_service.py
│   │   ├── fee_calculator.py
│   │   └── date_calculator.py
│   ├── validators/                # CPF/CNPJ validation
│   ├── middleware/                # Request logging middleware
│   ├── templates/
│   │   ├── contract_template.html
│   │   └── backups/               # Template backups
│   └── migrations/
├── contracts/                     # Generated PDFs
├── backups/                       # Database backups
├── tests/                         # pytest test suite
├── scripts/                       # Utility scripts
│   ├── backup_db.py
│   └── restore_db.py
├── frontend/                      # Next.js application
│   ├── app/                       # App Router pages
│   ├── components/                # React components
│   ├── lib/                       # Utilities, hooks, schemas
│   ├── store/                     # Zustand stores
│   └── tests/                     # Frontend tests with MSW
├── condominios_manager/           # Django settings
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml
├── .pre-commit-config.yaml        # Code quality hooks
└── manage.py
```

---

## Known Limitations

1. **PDF Generation**: Requires Chrome installed; Windows-specific path detection
2. **Late Fee Calculation**: Assumes 30-day months
3. **Payment Tracking**: No partial payment or payment history support
4. **Multi-tenancy**: Single organization/landlord design
5. **Localization**: Brazilian Portuguese only (dates, currency, documents)

---

## Migration Notes

### Migration Numbering
Migrations follow sequential numbering:
- `0001_initial.py` - Base schema
- `0002_lease_number_of_tenants.py` - Tenant count tracking
- `0003_refactor_database.py` - LeaseTenant model
- `0004_add_validators_and_indexes.py` - Field validators, indexes
- `0005_add_composite_indexes.py` - Performance indexes
- `0006_add_tenant_user_fk.py` - Tenant-User FK
- `0007_tenant_user.py` - Tenant portal access
- `0008_add_audit_softdelete_mixins.py` - Audit & soft delete fields

### LeaseTenant Table
The `LeaseTenant` model uses `db_table='core_lease_tenant_details'` to avoid conflicts with Django's auto-generated M2M table.

### Soft Delete Impact
After migration 0008, deleted records are preserved with `is_deleted=True`. Default querysets automatically exclude deleted records. Use `Model.objects.with_deleted()` to include them.
