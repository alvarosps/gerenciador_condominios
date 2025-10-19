# Architecture Diagrams
## Visual Reference for Condominios Manager

---

## 1. Current Architecture (Monolithic)

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT                                │
│                   (Frontend / API Consumer)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP Requests
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Django REST Framework                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LeaseViewSet.generate_contract()          │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ • Get lease from DB                              │  │ │
│  │  │ • Calculate dates (leap year logic)             │  │ │
│  │  │ • Calculate furniture (set operations)          │  │ │
│  │  │ • Calculate fees (50 vs 80)                     │  │ │
│  │  │ • Prepare template context                      │  │ │
│  │  │ • Render Jinja2 template                        │  │ │
│  │  │ • Launch Chrome (hardcoded path)                │  │ │
│  │  │ • Generate PDF                                  │  │ │
│  │  │ • Save to file system                           │  │ │
│  │  │ • Update database                               │  │ │
│  │  │ • Return HTTP response                          │  │ │
│  │  │                                                  │  │ │
│  │  │ Total: 113 lines, does EVERYTHING               │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Django ORM (Anemic Models)                │
│  • Building, Apartment, Tenant, Lease, Furniture            │
│  • Only data fields, no business logic                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       PostgreSQL Database                    │
└─────────────────────────────────────────────────────────────┘

PROBLEMS:
❌ All logic in one place (God Method)
❌ Impossible to unit test
❌ Tight coupling to frameworks
❌ Hardcoded configuration
❌ No reusability
❌ Mixed abstraction levels
```

---

## 2. Recommended Architecture (Layered + DDD)

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT                                │
│                   (Frontend / API Consumer)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP Requests
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          LeaseViewSet.generate_contract()              │ │
│  │  • Validate request                                    │ │
│  │  • Call service.generate_contract()                   │ │
│  │  • Format response                                     │ │
│  │  • Handle errors                                       │ │
│  │                                                         │ │
│  │  Total: ~15 lines, HTTP ONLY                           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           LeaseService.generate_contract()             │ │
│  │  • Get lease from repository                          │ │
│  │  • Prepare contract data (using domain methods)       │ │
│  │  • Call document service                              │ │
│  │  • Update lease status                                 │ │
│  │  • Save via repository                                 │ │
│  │                                                         │ │
│  │  Total: ~20 lines, ORCHESTRATION                       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     DOMAIN LAYER                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │               Lease Entity (Rich Model)                │ │
│  │  • calculate_final_date()        (uses domain service)│ │
│  │  • calculate_furniture_inventory() (business logic)   │ │
│  │  • calculate_total_value()                            │ │
│  │  • mark_contract_generated()                          │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Domain Services                            │ │
│  │  DateCalculationService:                               │ │
│  │    • calculate_final_date() (leap year logic)         │ │
│  │    • days_late()                                       │ │
│  │                                                         │ │
│  │  FeeCalculationEngine:                                 │ │
│  │    • calculate_late_fee()                             │ │
│  │    • calculate_tag_fee()                              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          DjangoLeaseRepository                         │ │
│  │  • get_by_id()                                        │ │
│  │  • save()                                             │ │
│  │  • Translates between ORM and Domain                   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │      DocumentGenerationService                         │ │
│  │  • Prepare template context                           │ │
│  │  • Render HTML                                         │ │
│  │  • Generate PDF (via generator)                       │ │
│  │  • Store file (via storage)                           │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─────────────────┐  ┌────────────────┐                   │
│  │ PyppeteerPDF    │  │ WeasyPrintPDF  │  (Pluggable!)     │
│  │ Generator       │  │ Generator      │                   │
│  └─────────────────┘  └────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER (ORM)                          │
│  • Lease, Apartment, Tenant models                          │
│  • Persistence only                                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                      │
└─────────────────────────────────────────────────────────────┘

BENEFITS:
✅ Clear separation of concerns
✅ Each layer has single responsibility
✅ Easy to unit test
✅ Business logic isolated
✅ Pluggable implementations
✅ Reusable components
```

---

## 3. Bounded Contexts (App Organization)

```
┌─────────────────────────────────────────────────────────────┐
│                  Condominios Manager System                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              PROPERTIES CONTEXT                       │  │
│  │  Manages buildings and apartments                     │  │
│  │  • Building                                           │  │
│  │  • Apartment                                          │  │
│  │  • Furniture                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↑ ↓                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                LEASES CONTEXT                         │  │
│  │  Manages rental contracts                             │  │
│  │  • Lease                                              │  │
│  │  • Contract generation                                │  │
│  │  • Fee calculations                                   │  │
│  │  • Date calculations                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↑ ↓                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               TENANTS CONTEXT                         │  │
│  │  Manages tenants and dependents                       │  │
│  │  • Tenant                                             │  │
│  │  • Dependent                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↑                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              DOCUMENTS CONTEXT                        │  │
│  │  Document generation (cross-cutting)                  │  │
│  │  • Contract PDF                                       │  │
│  │  • Receipt PDF (future)                               │  │
│  │  • Notice PDF (future)                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              FINANCES CONTEXT (Future)                │  │
│  │  Payment and expense tracking                         │  │
│  │  • Payment                                            │  │
│  │  • Expense                                            │  │
│  │  • Invoice                                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                SHARED KERNEL                          │  │
│  │  Common code used by all contexts                     │  │
│  │  • Value Objects (Money, CPF)                         │  │
│  │  • Base Entities                                      │  │
│  │  • Common Exceptions                                  │  │
│  │  • Utilities                                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Contract Generation Flow (Before)

```
API Request
    │
    ↓
┌─────────────────────────────────────────────────┐
│   LeaseViewSet.generate_contract() - 113 LINES  │
│   ┌──────────────────────────────────────────┐  │
│   │ 1. Get lease from DB                     │  │
│   │ 2. Calculate next_month_date             │  │
│   │     - relativedelta logic                │  │
│   │ 3. Calculate final_date                  │  │
│   │     - Add validity months                │  │
│   │     - Check Feb 29 edge case             │  │
│   │     - Handle leap year                   │  │
│   │ 4. Calculate tag fee                     │  │
│   │     - If 1 tenant: 50, else: 80          │  │
│   │ 5. Calculate total value                 │  │
│   │     - rental + cleaning + tags           │  │
│   │ 6. Calculate furniture inventory         │  │
│   │     - Set operations                     │  │
│   │ 7. Prepare template context              │  │
│   │ 8. Load Jinja2 environment               │  │
│   │ 9. Render HTML template                  │  │
│   │ 10. Create contracts directory           │  │
│   │ 11. Define PDF path                      │  │
│   │ 12. Launch Chrome browser                │  │
│   │     - Hardcoded path                     │  │
│   │ 13. Create new page                      │  │
│   │ 14. Write temp HTML file                 │  │
│   │ 15. Navigate to HTML                     │  │
│   │ 16. Generate PDF                         │  │
│   │ 17. Close browser                        │  │
│   │ 18. Delete temp HTML                     │  │
│   │ 19. Update lease.contract_generated      │  │
│   │ 20. Save to DB                           │  │
│   │ 21. Return HTTP response                 │  │
│   └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
    │
    ↓
HTTP Response

ISSUES:
• Mixing abstraction levels
• Multiple responsibilities
• Hard to test
• Hard to change
• Brittle
```

---

## 5. Contract Generation Flow (After)

```
API Request
    │
    ↓
┌──────────────────────────────────────────┐
│  LeaseViewSet.generate_contract()        │
│  • Validate request                      │
│  • Call service                          │
│  • Format response                       │
│  (15 lines)                              │
└──────────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────────┐
│  LeaseService.generate_contract()        │
│  • Get lease (repository)                │
│  • Prepare data (domain methods)         │
│  • Generate PDF (document service)       │
│  • Update lease (domain method)          │
│  • Save (repository)                     │
│  (20 lines)                              │
└──────────────────────────────────────────┘
    │
    ├─────────────────────────────────┐
    │                                 │
    ↓                                 ↓
┌──────────────────────┐  ┌──────────────────────────┐
│ Domain Methods       │  │ DocumentGenerationService│
│ • calculate_final()  │  │ • Prepare context        │
│ • calculate_furn()   │  │ • Render template        │
│ • calculate_total()  │  │ • Generate PDF           │
│ (Pure logic)         │  │ • Store file             │
└──────────────────────┘  └──────────────────────────┘
                              │
                              ├─────────────────┐
                              │                 │
                              ↓                 ↓
                    ┌──────────────┐  ┌──────────────┐
                    │ PDF Generator│  │ File Storage │
                    │ (Pluggable)  │  │ (Pluggable)  │
                    └──────────────┘  └──────────────┘
    │
    ↓
HTTP Response

BENEFITS:
• Single Responsibility Principle
• Easy to test each component
• Easy to swap implementations
• Clear flow
• Maintainable
```

---

## 6. Dependency Flow (Dependency Inversion)

```
┌─────────────────────────────────────────────────────────┐
│                    HIGH LEVEL                            │
│  ┌──────────┐           ┌──────────┐                    │
│  │   API    │────uses───│ AppLayer │                    │
│  │  Layer   │           │ Services │                    │
│  └──────────┘           └──────────┘                    │
│                              │                           │
│                         uses │                           │
│                              ↓                           │
│  ┌────────────────────────────────────────────────┐    │
│  │            DOMAIN LAYER                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐     │    │
│  │  │ Entities │  │ Services │  │Interface │     │    │
│  │  │          │  │          │  │  (IRepo) │     │    │
│  │  └──────────┘  └──────────┘  └──────────┘     │    │
│  │                                    ↑            │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                                        │
                               implements│
                                        │
┌─────────────────────────────────────────────────────────┐
│                    LOW LEVEL                             │
│  ┌────────────────────────────────────────────────┐    │
│  │        INFRASTRUCTURE LAYER                     │    │
│  │  ┌──────────────┐  ┌──────────────┐           │    │
│  │  │    Django    │  │ PDF Generator│           │    │
│  │  │ Repository   │  │              │           │    │
│  │  │ (implements  │  │              │           │    │
│  │  │   IRepo)     │  │              │           │    │
│  │  └──────────────┘  └──────────────┘           │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘

RULE: Dependencies always point INWARD
• Domain has NO dependencies on outer layers
• Infrastructure depends on Domain (via interfaces)
• Easy to test Domain in isolation
• Easy to swap Infrastructure implementations
```

---

## 7. Testing Pyramid

```
                    ┌──────────────┐
                    │     E2E      │  (Few, Slow)
                    │   Full API   │
                    │   Tests      │
                    └──────────────┘
                   ┌────────────────┐
                   │  Integration   │   (Some, Medium)
                   │   Tests        │
                   │ • Service tests│
                   │ • Repository   │
                   └────────────────┘
              ┌──────────────────────┐
              │    Unit Tests        │    (Many, Fast)
              │  • Domain entities   │
              │  • Domain services   │
              │  • Business logic    │
              │  • Pure functions    │
              └──────────────────────┘

CURRENT:  Only integration tests (slow, brittle)
GOAL:     Pyramid structure (fast, reliable)

Example test speeds:
• Unit: < 1ms per test
• Integration: 10-100ms per test
• E2E: 1-5 seconds per test

With 100 unit tests:  < 100ms total
With 20 integration:   2 seconds
With 5 E2E:           10 seconds
Total:                ~12 seconds (acceptable)
```

---

## 8. Data Flow: Create Lease

```
Frontend
   │
   │ POST /api/leases/
   │ { apartment_id, tenant_id, ... }
   ↓
┌────────────────────────────────────┐
│ LeaseViewSet.create()              │
│ • Validate request data            │
│ • Create DTO                       │
└────────────────────────────────────┘
   │
   ↓
┌────────────────────────────────────┐
│ LeaseService.create_lease()        │
│ • Get apartment (repository)       │
│ • Get tenants (repository)         │
│ • Validate business rules          │
│ • Create domain entity             │
│ • Save via repository              │
└────────────────────────────────────┘
   │
   ├─────────────────────────┐
   │                         │
   ↓                         ↓
┌──────────────┐  ┌────────────────────┐
│ Domain       │  │ Repository         │
│ Validation   │  │ • map to ORM       │
│ • max tenants│  │ • save to DB       │
│ • apt avail  │  │ • return entity    │
└──────────────┘  └────────────────────┘
   │
   ↓
Database
```

---

## 9. Configuration Flow

```
┌──────────────┐
│   .env file  │
│ (Not in git) │
└──────────────┘
      │
      │ Read by python-decouple
      ↓
┌──────────────────────────────┐
│  config/settings/base.py     │
│  • Parse env vars            │
│  • Set Django settings       │
│  • Create config dicts       │
└──────────────────────────────┘
      │
      ↓
┌──────────────────────────────┐
│  apps/shared/infra/config.py │
│  AppConfig class             │
│  • get_pdf_chrome_path()     │
│  • get_tag_fee_single()      │
│  • get_late_fee_rate()       │
└──────────────────────────────┘
      │
      │ Used by
      ↓
┌──────────────────────────────┐
│  Domain Services             │
│  • FeeCalculationEngine      │
│  • DateCalculationService    │
└──────────────────────────────┘
      │
      ↓
┌──────────────────────────────┐
│  Infrastructure              │
│  • PDF Generators            │
│  • Storage                   │
└──────────────────────────────┘

BENEFITS:
• Single source of truth (.env)
• Easy to change per environment
• No secrets in code
• Type safety via config class
```

---

## 10. Scaling Strategy

```
CURRENT (Single Server)
┌────────────────────────────┐
│    Django Application      │
│ • API                      │
│ • Business Logic           │
│ • PDF Generation           │
│ • File Storage             │
└────────────────────────────┘
           │
           ↓
┌────────────────────────────┐
│      PostgreSQL            │
└────────────────────────────┘

PHASE 1: Add Caching
┌────────────────────────────┐
│    Django Application      │
└────────────────────────────┘
     │             │
     ↓             ↓
┌────────┐   ┌────────┐
│ Redis  │   │  DB    │
│ Cache  │   │        │
└────────┘   └────────┘

PHASE 2: Add Background Jobs
┌────────────────────────────┐
│    Django API              │
└────────────────────────────┘
     │
     ↓
┌────────────────────────────┐
│    Celery Workers          │
│ • PDF Generation (async)   │
│ • Email notifications      │
└────────────────────────────┘
     │
     ↓
┌────────────────────────────┐
│    Redis Queue             │
└────────────────────────────┘

PHASE 3: Separate Services (if needed)
┌───────────┐  ┌──────────────┐  ┌──────────┐
│  API      │  │  Document    │  │ Payment  │
│  Gateway  │─>│  Service     │  │ Service  │
│           │  │              │  │          │
└───────────┘  └──────────────┘  └──────────┘
     │              │                 │
     ↓              ↓                 ↓
     Database    File Store      Payment Gateway

PHASE 4: Multi-Tenant
┌────────────────────────────┐
│  Organization A            │
│    Buildings, Leases       │
└────────────────────────────┘
┌────────────────────────────┐
│  Organization B            │
│    Buildings, Leases       │
└────────────────────────────┘
     │
     ↓
┌────────────────────────────┐
│  Shared Database           │
│  (with org_id isolation)   │
└────────────────────────────┘
```

---

**Document Version:** 1.0
**Author:** Claude (Backend Architecture Specialist)
**Date:** 2025-10-19
