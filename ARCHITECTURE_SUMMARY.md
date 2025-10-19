# Architecture Summary: Condominios Manager
## Quick Reference Guide

---

## Current vs Recommended Architecture

### Current State: Monolithic MVT

```
API Layer (ViewSets)
- HTTP handling
- Business logic (100+ lines)
- Date calculations
- PDF generation
- Fee calculations
- Template rendering
- File operations
       ↓
Serializers
- Data transformation
- Nested object creation
       ↓
Django ORM Models
- Data only (anemic)
       ↓
PostgreSQL
```

**Problems:** Business logic in views, tight coupling, hard to test, no reusability, hardcoded configuration

---

### Recommended State: Layered Architecture + DDD Lite

```
API LAYER
├── ViewSets (HTTP only)
├── Serializers
└── DTOs
       ↓
APPLICATION LAYER
└── Application Services
    ├── LeaseService (orchestration)
    ├── DocumentGenerationService
    └── FinancialService (future)
       ↓
DOMAIN LAYER
├── Domain Entities (Rich Models)
│   ├── Lease.calculate_late_fee()
│   ├── Lease.calculate_furniture_inventory()
│   └── Lease.change_due_date()
├── Domain Services
│   ├── DateCalculationService
│   └── FeeCalculationEngine
└── Repository Interfaces
       ↓
INFRASTRUCTURE LAYER
├── Repository Implementations
│   └── DjangoLeaseRepository
└── External Integrations
    ├── PyppeteerPDFGenerator
    ├── WeasyPrintGenerator
    └── FileSystemStorage
       ↓
DATA LAYER
└── Django ORM Models (persistence only)
```

**Benefits:** Clear separation, business logic in domain, easy to test, reusable, flexible

---

## File Structure Comparison

### Current
```
core/
├── models.py              (All 6 models)
├── views.py               (198 lines: everything)
├── serializers.py
├── utils.py
└── templates/
```

### Recommended
```
apps/
├── properties/            (Building, Apartment)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── api/
├── leases/                (Lease)
│   ├── domain/
│   │   ├── entities.py
│   │   ├── services.py    (DateCalculationService)
│   │   └── repositories.py
│   ├── application/
│   │   └── services.py    (LeaseService)
│   ├── infrastructure/
│   └── api/
├── tenants/               (Tenant, Dependent)
├── documents/             (PDF generation)
│   ├── domain/
│   ├── application/
│   └── infrastructure/
│       └── pdf_generators/
├── finances/              (Future)
└── shared/                (Common code)
```

---

## Key Improvements

### 1. Configuration Management

**Before:**
```python
# Hardcoded everywhere
executablePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
PASSWORD = 'postgres'
valor_tags = 50 if len(tenants) == 1 else 80
```

**After:**
```bash
# .env
PDF_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
DB_PASSWORD=postgres
FEE_TAG_SINGLE=50.00
```

```python
# Access via config
chrome_path = AppConfig.get_pdf_chrome_path()
tag_fee = FeeCalculationEngine.calculate_tag_fee(num_tenants)
```

### 2. Business Logic Location

**Before:** In ViewSets (views.py)
```python
# 113 lines in one method
def generate_contract(self, request, pk=None):
    # Date calculations
    # Furniture logic
    # Template rendering
    # PDF generation
    # All mixed together!
```

**After:** In Domain Layer
```python
# Domain entity
class Lease:
    def calculate_final_date(self):
        return DateCalculationService.calculate_final_date(...)

    def calculate_furniture_inventory(self):
        return list(apt_furniture - tenant_furniture)

# Domain service
class DateCalculationService:
    @staticmethod
    def calculate_final_date(start, months):
        # Leap year logic here
```

### 3. Testability

**Before:** Integration tests only (slow, brittle)
```python
# Needs DB, Chrome, file system
def test_generate_contract():
    lease = Lease.objects.create(...)
    response = client.post('/api/leases/1/generate_contract/')
    assert os.path.exists(response.data['pdf_path'])
```

**After:** Unit + Integration (fast, reliable)
```python
# Unit test (milliseconds, no dependencies)
def test_calculate_final_date():
    result = DateCalculationService.calculate_final_date(
        date(2025, 1, 15), 12
    )
    assert result == date(2026, 1, 15)

# Service test (with mocks)
def test_generate_contract_service():
    mock_repo.get_by_id.return_value = lease
    path = service.generate_contract(1)
    assert path == "/path/to/pdf"
```

---

## Migration Strategy

### Week 1: Foundation
- [x] Environment configuration (.env)
- [x] Settings refactoring (base/dev/prod)
- [x] Create app structure
- [x] Set up testing

### Week 2: Domain Layer
- [x] Extract domain services
- [x] Write unit tests
- [x] Update views to use services

### Week 3: Application Layer
- [x] Create repositories
- [x] Create application services
- [x] Set up dependency injection

### Week 4: Refactoring
- [x] Refactor ViewSets
- [x] Integration tests
- [x] Documentation

---

## Code Organization Rules

| What | Where | Example |
|------|-------|---------|
| Business Rules | Domain Layer | Late fee = 5% per day |
| Use Cases | Application Layer | "Generate contract" workflow |
| HTTP | API Layer | Request/response handling |
| Database | Infrastructure | ORM queries |
| External Services | Infrastructure | PDF, storage |
| Configuration | .env + config.py | Paths, credentials |

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| ViewSet Lines | 198 | < 50 |
| Business Logic | Views | Domain |
| Test Coverage | 0% | > 80% |
| Unit Test Speed | N/A | < 1s |
| Configuration | Hardcoded | .env |

---

## Key Design Patterns Used

1. **Layered Architecture** - Clear separation of concerns
2. **Repository Pattern** - Abstract data access
3. **Dependency Injection** - Testable, flexible
4. **Strategy Pattern** - Pluggable PDF generators
5. **Domain-Driven Design** - Rich domain models

---

## Quick Commands

```bash
# Install dependencies
pip install python-decouple dependency-injector pytest pytest-django

# Run tests
pytest tests/domain/          # Unit tests (fast)
pytest tests/integration/     # Integration tests

# Run with specific environment
DJANGO_ENV=development python manage.py runserver
DJANGO_ENV=production python manage.py runserver

# Create new bounded context
python manage.py startapp new_app apps/new_app
mkdir -p apps/new_app/{domain,application,infrastructure,api}
```

---

## Resources

- **Detailed Analysis:** `ARCHITECTURAL_ANALYSIS.md` (60+ pages)
- **Before/After Example:** `REFACTORING_EXAMPLE.md` (contract generation)
- **Step-by-Step Guide:** `MIGRATION_GUIDE.md` (day-by-day plan)

---

**Version:** 1.0
**Author:** Claude (Backend Architecture Specialist)
**Date:** 2025-10-19
