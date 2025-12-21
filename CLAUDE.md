# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Condomínios Manager is a property management system for rental properties in Brazil. The backend is fully implemented with Django REST Framework (100% complete), while the frontend was recently removed and is being rebuilt from scratch.

**Tech Stack:**
- Backend: Django 5.0.2, Django REST Framework 3.14.0, PostgreSQL
- PDF Generation: pyppeteer, ReportLab
- Key Libraries: num2words (for currency in words), Pillow (image handling)

## Architecture

### Data Model Hierarchy

The system follows this relational structure:

```
Building (Prédio)
  └─ Apartment (Apartamento)
       └─ Lease (Locação)
            └─ Tenant (Inquilino)
                 └─ Dependent (Dependente)

Furniture (Móvel) - Many-to-Many with both Apartment and Tenant
```

**Key Relationships:**
- `Apartment.furnitures` - furniture provided with the apartment
- `Tenant.furnitures` - tenant's own furniture
- Lease furniture = Apartment furniture minus Tenant furniture
- `Lease.responsible_tenant` - the tenant responsible for the contract
- `Lease.tenants` - all tenants living in the apartment (many-to-many)

### Core Business Logic

**Contract Generation (`core/views.py:generate_contract`):**
- Generates PDF contracts using Jinja2 templates and pyppeteer
- Chrome executable path is hardcoded: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Furniture in contract = Apartment furniture - Responsible tenant furniture
- Tag fee: R$50 for 1 tenant, R$80 for 2+ tenants
- Uses `contract_template.html` from `core/templates/`
- PDFs saved to: `contracts/{building_number}/contract_apto_{apt_number}_{lease_id}.pdf`

**Date Calculations (Special Cases):**
- Handles leap year edge cases (Feb 29 → Feb 28 → March 1)
- Next month date: start_date + 1 month
- Final date: start_date + validity_months

**Fee Calculations:**
- Late fee: 5% per day based on daily rate (rental_value / 30)
- Due date change fee: daily_rate × days_difference

### API Endpoints

Base URL: `/api/`

**Standard CRUD:**
- `GET/POST /api/buildings/`
- `GET/PUT/PATCH/DELETE /api/buildings/{id}/`
- Same pattern for: `apartments`, `tenants`, `leases`, `furnitures`

**Special Lease Endpoints:**
- `POST /api/leases/{id}/generate_contract/` - Generate PDF contract
- `GET /api/leases/{id}/calculate_late_fee/` - Calculate late payment fees
- `POST /api/leases/{id}/change_due_date/` - Change due date with fee calculation
  - Body: `{"new_due_day": <1-31>}`

### Serializer Patterns

All serializers follow this pattern for foreign keys:
- Read: nested serializer (e.g., `building: BuildingSerializer`)
- Write: `_id` field (e.g., `building_id: PrimaryKeyRelatedField`)

**Many-to-Many handling:**
- Read: nested serializer (e.g., `furnitures: FurnitureSerializer`)
- Write: `_ids` field (e.g., `furniture_ids: PrimaryKeyRelatedField(many=True)`)

**Nested Creation:**
- Tenants can be created with dependents in a single request
- Dependents data goes in `dependents` array in tenant payload

## Development Commands

### Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Database setup (PostgreSQL must be running)
# Database credentials in settings.py:
# - NAME: condominio
# - USER: postgres
# - PASSWORD: postgres
# - HOST: localhost
# - PORT: 5432

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Access API at http://localhost:8000/api/
# Access admin at http://localhost:8000/admin/
```

### Database

```bash
# Make migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Shell access
python manage.py shell
```

## Important Configuration

### CORS Configuration

Frontend is expected to run on:
- `http://localhost:6000` (React default)
- `http://localhost:5173` (Vite default)

CORS is configured with credentials support in `settings.py`.

### Security Notes

- `SECRET_KEY` is exposed in settings.py (change for production)
- `DEBUG = True` (must be False in production)
- `ALLOWED_HOSTS = []` (configure for production)
- REST Framework: `AllowAny` permissions (add authentication for production)

### PDF Generation Requirements

- Requires Chrome/Chromium installed
- Windows path hardcoded in `core/views.py:121`
- Uses Windows-specific event loop policy (`WindowsSelectorEventLoopPolicy`)
- Temporary HTML files created during generation

## Data Validation

### Brazilian-Specific Fields

- `cpf_cnpj`: CPF for individuals, CNPJ for companies
- `is_company`: Boolean flag to distinguish person/company
- `marital_status`: Estado civil (required for tenants)
- Phone numbers stored as strings (no specific format enforced)

### Constraints

- `Building.street_number`: Unique positive integer
- `Apartment`: Unique together (building, number)
- `Lease.apartment`: OneToOne (one active lease per apartment)
- `Tenant.cpf_cnpj`: Unique
- Decimal fields use 2 decimal places, max 10 digits

## File Structure

```
condominios_manager/
├── core/                      # Main Django app
│   ├── models.py             # Data models
│   ├── serializers.py        # DRF serializers
│   ├── views.py              # API views and business logic
│   ├── urls.py               # API routing
│   ├── contract_rules.py     # Condominium rules text
│   ├── utils.py              # Helpers (format_currency, number_to_words)
│   └── templates/
│       └── contract_template.html  # PDF contract template
├── contracts/                # Generated PDFs (by building number)
│   ├── 836/
│   └── 850/
├── condominios_manager/      # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py
```

## Frontend Integration Notes

The frontend was removed. When rebuilding:

1. **API Integration**: Use `/api/` base URL with standard REST conventions
2. **Contract Download**: After calling `generate_contract`, retrieve PDF from returned `pdf_path`
3. **Furniture Management**: Handle apartment furniture vs tenant furniture distinction
4. **Lease Creation**: Multi-step form recommended (select apartment → tenants → terms → review)
5. **Date Handling**: Display dates in DD/MM/YYYY format (Brazilian standard)
6. **Currency**: Display in R$ format with 2 decimal places

## Testing

No test suite currently exists. When adding tests:
- Use Django's TestCase for models and views
- Test contract generation with mocked pyppeteer
- Test date calculations including edge cases (Feb 29)
- Test fee calculations with various scenarios

## Common Patterns

### Creating a Lease

```python
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

### Creating a Tenant with Dependents

```python
POST /api/tenants/
{
  "name": "João Silva",
  "cpf_cnpj": "123.456.789-00",
  "phone": "(11) 98765-4321",
  "marital_status": "Casado",
  "profession": "Engenheiro",
  "furniture_ids": [1, 2, 3],
  "dependents": [
    {"name": "Maria Silva", "phone": "(11) 91234-5678"}
  ]
}
```

## Known Issues & Limitations

- Pyppeteer can be slow for PDF generation (consider alternatives like WeasyPrint)
- No authentication/authorization system
- No audit trail for changes
- Hardcoded Chrome path limits cross-platform compatibility
- Late fee calculation assumes 30-day months
- No support for partial payments or payment history tracking
