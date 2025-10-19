# Architecture Quick Reference Guide
## Condomínios Manager - Backend Refactoring

**Last Updated:** October 19, 2025

---

## 🎯 TL;DR - What You Need to Know

**Current Grade:** C- (Functional but not maintainable)
**Refactoring Time:** 16 weeks
**ROI:** Saves 6+ weeks in future development
**Risk Level:** Low (phased approach with rollback plans)

---

## 🚨 Critical Issues (Must Fix Before New Features)

### 1. Business Logic in Views
**Problem:** 113-line method with 9 responsibilities
**File:** `core/views.py:48-160`
**Fix:** Extract to service layer (Week 2-4)

### 2. Zero Test Coverage
**Problem:** No tests = high bug risk
**Fix:** Add pytest + write tests (Week 1-2)

### 3. Hardcoded Secrets
**Problem:** Database password in version control
**File:** `condominios_manager/settings.py:83-84`
**Fix:** Move to `.env` files (Week 1, Day 1)

### 4. No Type Hints
**Problem:** No static type checking
**Fix:** Add type hints to all functions (Week 1-2)

### 5. Data Redundancy
**Problem:** Same fields in Apartment and Lease
**Fix:** Database migration to remove duplicates (Week 7-8)

---

## 📊 Where We Are vs Where We Need to Be

| Aspect | Current | Target | Action |
|--------|---------|--------|--------|
| **Testing** | 0% coverage | 90% | Add pytest framework |
| **Architecture** | Monolithic views | 5-layer architecture | Extract services |
| **Type Safety** | No type hints | 100% typed | Add type annotations |
| **Database** | 2/5 normalization | 4/5 normalization | Remove redundancy |
| **Security** | Exposed secrets | Environment vars | Create .env files |
| **Documentation** | No docstrings | Full documentation | Add docstrings |

---

## 🗺️ Refactoring Roadmap (16 Weeks)

### Phase 0: Setup (Week 1)
**What:** Environment config, backups, tooling
**Deliverable:** `.env` files, backup scripts, CI tools
**Effort:** 1 week

### Phase 1: Foundation (Weeks 2-3)
**What:** Testing framework, type hints, logging
**Deliverable:** 60% test coverage, type hints added
**Effort:** 2 weeks

### Phase 2: Service Layer (Weeks 4-6) ⭐ CRITICAL
**What:** Extract business logic from views
**Deliverable:** FeeCalculatorService, ContractService, DateCalculatorService
**Effort:** 3 weeks

### Phase 3: Domain Refinement (Weeks 7-8)
**What:** Add Payment model, remove duplicate fields
**Deliverable:** Payment tracking, cleaner schema
**Effort:** 2 weeks

### Phase 4: Infrastructure (Weeks 9-10)
**What:** Abstract PDF generation, make swappable
**Deliverable:** PDFGenerator interface, multiple implementations
**Effort:** 2 weeks

### Phase 5: Database Optimization (Weeks 11-12)
**What:** Add indexes, optimize queries
**Deliverable:** 40-60% query performance improvement
**Effort:** 2 weeks

### Phase 6: Security (Week 13)
**What:** Authentication, authorization, security audit
**Deliverable:** Secure API with auth
**Effort:** 1 week

### Phase 7: Advanced Features (Weeks 14-15)
**What:** Repository pattern, dashboard foundation
**Deliverable:** Ready for payment tracking, dashboards
**Effort:** 2 weeks

### Phase 8: Cleanup (Week 16)
**What:** Documentation, final testing
**Deliverable:** Production-ready codebase
**Effort:** 1 week

---

## 🎬 Getting Started - Week 1 Tasks

### Day 1: Security (IMMEDIATE)
```bash
# 1. Create .env file
cp .env.example .env

# 2. Edit .env with your credentials
DJANGO_SECRET_KEY=your-new-secret-key-here
DB_NAME=condominio
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432
CHROME_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

### Day 2: Backup
```bash
# Create database backup
python manage.py dumpdata > backup_$(date +%Y%m%d).json
pg_dump condominio > backup_$(date +%Y%m%d).sql
```

### Day 3: Testing Setup
```bash
# Install pytest
pip install pytest pytest-django pytest-cov factory-boy

# Create pytest.ini
# Copy from PHASED_REFACTORING_PLAN.md

# Write first test
# See tests/test_models.py example
```

### Day 4: Code Quality Tools
```bash
# Install tools
pip install black isort flake8 mypy django-stubs

# Create config files
# Copy from PHASED_REFACTORING_PLAN.md

# Run first formatting
black .
isort .
```

### Day 5: Type Hints Start
```python
# Add to core/utils.py
from typing import Union
from decimal import Decimal

def format_currency(value: Union[int, float, Decimal]) -> str:
    """Format numeric value as Brazilian currency."""
    return f"R$ {value:,.2f}"
```

---

## 📁 New File Structure (After Refactoring)

```
condominios_manager/
├── core/
│   ├── models.py                    # Domain models (data only)
│   ├── serializers.py               # DRF serializers (no logic)
│   ├── views.py                     # ViewSets (HTTP only, <50 lines/method)
│   ├── services/                    # 🆕 Business logic
│   │   ├── fee_calculator_service.py
│   │   ├── date_calculator_service.py
│   │   ├── contract_service.py
│   │   └── payment_service.py
│   ├── repositories/                # 🆕 Data access
│   │   ├── lease_repository.py
│   │   └── payment_repository.py
│   ├── infrastructure/              # 🆕 External services
│   │   ├── pdf/
│   │   │   ├── base.py              # PDFGenerator interface
│   │   │   ├── pyppeteer_generator.py
│   │   │   └── weasyprint_generator.py
│   │   └── storage/
│   │       └── file_storage.py
│   └── constants.py                 # 🆕 Magic numbers
├── tests/                           # 🆕 Test suite
│   ├── unit/
│   ├── integration/
│   └── factories.py
├── .env                             # 🆕 Environment config
└── requirements.txt
```

---

## 🔑 Key Metrics to Track

### Weekly Checklist

**Week 1:**
- [ ] `.env` file created
- [ ] Database backed up
- [ ] pytest installed and first test passes
- [ ] black/isort configured
- [ ] Type hints added to utils.py

**Week 2-3:**
- [ ] 60% test coverage achieved
- [ ] Type hints in all public methods
- [ ] CI/CD pipeline running
- [ ] Logging configured

**Week 4-6:**
- [ ] FeeCalculatorService extracted
- [ ] ContractService extracted
- [ ] LeaseViewSet.generate_contract <50 lines
- [ ] 90% coverage on services

**Week 7+:**
- [ ] Payment model added
- [ ] Duplicate fields removed
- [ ] PDFGenerator interface created
- [ ] Repository pattern implemented

---

## 🚀 Quick Commands

### Run Tests
```bash
pytest                           # Run all tests
pytest --cov=core                # With coverage
pytest -v                        # Verbose
pytest tests/unit/               # Unit tests only
```

### Code Quality
```bash
black .                          # Format code
isort .                          # Sort imports
flake8                           # Lint
mypy core/                       # Type check
```

### Database
```bash
python manage.py makemigrations  # Create migration
python manage.py migrate         # Apply migration
python manage.py dbshell         # SQL shell
```

### CI/CD
```bash
git push origin feature-branch   # Triggers GitHub Actions
# View results at: https://github.com/your-repo/actions
```

---

## 📚 Document Reference

| Document | Purpose | Read When |
|----------|---------|-----------|
| `COMPREHENSIVE_ARCHITECTURE_REPORT.md` | Executive overview | Before starting |
| `PHASED_REFACTORING_PLAN.md` | Detailed weekly tasks | Weekly planning |
| `ARCHITECTURAL_ANALYSIS.md` | Technical design | Implementation phase |
| `DATABASE_ARCHITECTURE_ANALYSIS.md` | Schema improvements | Week 7-8 |
| `REFACTORING_EXAMPLE.md` | Before/after code | When refactoring |
| `MIGRATION_GUIDE.md` | Step-by-step guide | Daily reference |

---

## ❓ FAQ

### Q: Can we add new features during refactoring?
**A:** Not recommended until Phase 2 (Week 6) is complete. New features will require rework if architecture changes.

### Q: What if we need to deploy urgently during refactoring?
**A:** Each phase is independently deployable. Use feature flags to control new code paths.

### Q: How do we handle breaking changes?
**A:** We don't. The plan maintains 100% API backward compatibility until final cutover.

### Q: What if a phase takes longer than planned?
**A:** Adjust timeline but don't skip phases. Foundation (Phase 1-2) is critical.

### Q: Can we skip testing?
**A:** No. Tests are the safety net that allows confident refactoring.

---

## 🆘 Getting Help

### Issues During Refactoring

1. **Tests failing after refactoring:**
   - Check backward compatibility
   - Review test fixtures
   - Validate mock data

2. **Performance regression:**
   - Run database query analysis
   - Check N+1 queries
   - Review eager loading

3. **Merge conflicts:**
   - Rebase frequently
   - Communicate with team
   - Use small commits

---

## 📞 Support Resources

**Code Examples:** See `REFACTORING_EXAMPLE.md`
**Migration Scripts:** See `MIGRATION_GUIDE.md`
**Architecture Diagrams:** See `ARCHITECTURAL_ANALYSIS.md`
**Database Schema:** See `DATABASE_ARCHITECTURE_ANALYSIS.md`

---

## ✅ Definition of Done (Per Phase)

A phase is complete when:
- [ ] All tasks in phase completed
- [ ] Tests pass (coverage target met)
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Performance validated
- [ ] Deployment successful
- [ ] Rollback tested

---

## 🎯 Success Criteria (Overall)

At the end of 16 weeks:
- ✅ 90% test coverage
- ✅ 100% type hints
- ✅ <20 lines per method average
- ✅ Service layer for all business logic
- ✅ Clean database schema
- ✅ Secure configuration
- ✅ CI/CD pipeline operational
- ✅ Ready for payment tracking
- ✅ Ready for dashboards
- ✅ Ready for multi-document generation

---

**Remember:** Slow is smooth, smooth is fast. Take time to build the foundation correctly.

**Next Step:** Read `COMPREHENSIVE_ARCHITECTURE_REPORT.md` for full context.
