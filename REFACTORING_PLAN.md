# Condomínios Manager - Comprehensive Refactoring Plan

**Document Version:** 1.0
**Date:** 2025-10-19
**Estimated Total Duration:** 12-16 weeks
**Team Size Assumption:** 1-2 developers

---

## Executive Summary

This refactoring plan transforms the Condomínios Manager from a monolithic Django application into a well-architected, maintainable system following SOLID principles, DDD patterns, and industry best practices. The plan prioritizes **zero-downtime deployment**, **backward compatibility**, and **incremental progress** while addressing critical technical debt.

### Critical ChromaDB Integration Opportunity

**IMPORTANT**: Before implementing advanced search features or document management systems, evaluate ChromaDB for:
- **Semantic search** across contracts, leases, and tenant information
- **Document indexing** for PDFs and contracts
- **Knowledge base** for building/apartment specifications and history
- **Audit trail storage** with semantic querying capabilities

ChromaDB can provide powerful search capabilities without external dependencies. Evaluate during Phase 4 (Infrastructure Improvements).

### Key Objectives

1. **Separate Concerns**: Implement layered architecture (Presentation → Application → Domain → Infrastructure)
2. **Eliminate Technical Debt**: Address SOLID violations, add type hints, implement proper error handling
3. **Enable Future Features**: Financial tracking, payment management, multi-document support
4. **Maintain Stability**: Zero breaking changes to existing API during transition
5. **Improve Quality**: Achieve 80%+ test coverage

### Current State Assessment

| Category | Score | Issues |
|----------|-------|--------|
| Architecture | 2/10 | Monolithic, fat views, no layering |
| SOLID Compliance | 3/10 | Multiple SRP violations, hardcoded dependencies |
| Code Quality | 4/10 | No type hints, no docstrings, poor error handling |
| Database Design | 5/10 | Data redundancy, missing audit trail |
| Testing | 0/10 | Zero test coverage |
| Security | 3/10 | Exposed credentials, DEBUG=True, AllowAny permissions |

---

## Phase Overview

| Phase | Duration | Status | Priority | Risk |
|-------|----------|--------|----------|------|
| 0: Pre-Refactoring Setup | 1 week | ⏳ Pending | Critical | Low |
| 1: Foundation & Testing Infrastructure | 2 weeks | ⏳ Pending | Critical | Low |
| 2: Service Layer Extraction | 3 weeks | ⏳ Pending | Critical | Medium |
| 3: Domain Model Refinement | 2 weeks | ⏳ Pending | High | Medium |
| 4: Infrastructure Improvements | 2 weeks | ⏳ Pending | High | Medium |
| 5: Database Normalization | 2 weeks | ⏳ Pending | High | High |
| 6: Security & Configuration | 1 week | ⏳ Pending | High | Low |
| 7: Advanced Features Foundation | 2 weeks | ⏳ Pending | Medium | Medium |
| 8: Cleanup & Documentation | 1 week | ⏳ Pending | Medium | Low |

**Total Estimated Duration:** 16 weeks (4 months)

---

## Phase 0: Pre-Refactoring Setup

**Duration:** 1 week (5 days)
**Priority:** Critical
**Risk:** Low
**Dependencies:** None

### Objectives

- Establish safety nets before making changes
- Create baseline for measuring improvements
- Set up development workflow
- Document current system behavior

### Tasks

#### Day 1: Version Control & Branching Strategy

**Task 0.1.1: Create Development Branch** (2 hours)
```bash
git checkout -b refactoring/phase-0-setup
git push -u origin refactoring/phase-0-setup
```

**Task 0.1.2: Document Branching Strategy** (1 hour)
- Create `.github/CONTRIBUTING.md` or `docs/BRANCHING_STRATEGY.md`
- Strategy: Feature branching with protected master
  - `master` - production-ready code
  - `develop` - integration branch
  - `refactoring/phase-X-name` - phase-specific branches
  - `feature/brief-description` - individual features

**Task 0.1.3: Set Up Git Hooks** (1 hour)
```bash
# Install pre-commit framework
pip install pre-commit

# Create .pre-commit-config.yaml
```

#### Day 2: Development Environment Standardization

**Task 0.2.1: Create Environment Configuration** (3 hours)
- Create `.env.example` file
- Move hardcoded values to environment variables
- Document all required environment variables

**File: `.env.example`**
```bash
# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=condominio
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PDF Generation
CHROME_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
PDF_OUTPUT_DIR=contracts

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Application Settings
PAGE_SIZE=20
DEFAULT_TAG_FEE_SINGLE=50.00
DEFAULT_TAG_FEE_MULTIPLE=80.00
```

**Task 0.2.2: Install python-decouple** (1 hour)
```bash
pip install python-decouple
pip freeze > requirements.txt
```

**Task 0.2.3: Update settings.py** (2 hours)

**File: `C:\Users\alvarosps\git\condominios_manager\condominios_manager\settings.py`** (partial update)
```python
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY', default='django-insecure-b7ya%t^1&z1v#af1mlzjsm*$l9o^zj!h9a3*)tf@2k&z8b*^)h')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Database
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='condominio'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# PDF Generation
CHROME_EXECUTABLE_PATH = config(
    'CHROME_EXECUTABLE_PATH',
    default=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
)
PDF_OUTPUT_DIR = config('PDF_OUTPUT_DIR', default='contracts')

# Application Constants
DEFAULT_TAG_FEE_SINGLE = config('DEFAULT_TAG_FEE_SINGLE', default=50.00, cast=float)
DEFAULT_TAG_FEE_MULTIPLE = config('DEFAULT_TAG_FEE_MULTIPLE', default=80.00, cast=float)
```

#### Day 3: Database Backup & Migration Safety

**Task 0.3.1: Create Backup Script** (2 hours)

**File: `C:\Users\alvarosps\git\condominios_manager\scripts\backup_db.py`**
```python
"""
Database backup utility
Usage: python scripts/backup_db.py
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path
from decouple import config

def backup_database():
    """Create PostgreSQL database backup"""
    db_name = config('DB_NAME', default='condominio')
    db_user = config('DB_USER', default='postgres')
    db_host = config('DB_HOST', default='localhost')
    db_port = config('DB_PORT', default='5432')

    backup_dir = Path(__file__).parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'backup_{db_name}_{timestamp}.sql'

    # Set password environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = config('DB_PASSWORD', default='postgres')

    # Execute pg_dump
    cmd = [
        'pg_dump',
        '-h', db_host,
        '-p', db_port,
        '-U', db_user,
        '-F', 'c',  # Custom format
        '-b',  # Include blobs
        '-v',  # Verbose
        '-f', str(backup_file),
        db_name
    ]

    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"✓ Backup created successfully: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"✗ Backup failed: {e}")
        return None

if __name__ == '__main__':
    backup_database()
```

**Task 0.3.2: Create Restore Script** (1 hour)

**File: `C:\Users\alvarosps\git\condominios_manager\scripts\restore_db.py`**
```python
"""
Database restore utility
Usage: python scripts/restore_db.py path/to/backup.sql
"""
import os
import sys
import subprocess
from decouple import config

def restore_database(backup_file):
    """Restore PostgreSQL database from backup"""
    db_name = config('DB_NAME', default='condominio')
    db_user = config('DB_USER', default='postgres')
    db_host = config('DB_HOST', default='localhost')
    db_port = config('DB_PORT', default='5432')

    env = os.environ.copy()
    env['PGPASSWORD'] = config('DB_PASSWORD', default='postgres')

    cmd = [
        'pg_restore',
        '-h', db_host,
        '-p', db_port,
        '-U', db_user,
        '-d', db_name,
        '-c',  # Clean (drop) database objects before recreating
        '-v',  # Verbose
        backup_file
    ]

    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"✓ Database restored successfully from: {backup_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Restore failed: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_db.py path/to/backup.sql")
        sys.exit(1)

    restore_database(sys.argv[1])
```

**Task 0.3.3: Create Initial Backup** (30 minutes)
```bash
python scripts/backup_db.py
```

#### Day 4: Code Quality Tools Setup

**Task 0.4.1: Install Development Dependencies** (1 hour)
```bash
pip install black isort flake8 mypy pylint bandit safety
pip freeze > requirements-dev.txt
```

**Task 0.4.2: Configure Code Formatters** (2 hours)

**File: `pyproject.toml`**
```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
  | migrations
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
skip_gitignore = true
skip = ["migrations", ".venv"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start with false, gradually enable
ignore_missing_imports = true
exclude = ['migrations/']

[tool.pylint.messages_control]
disable = ["C0330", "C0326", "missing-module-docstring"]

[tool.pylint.format]
max-line-length = 100
```

**File: `.flake8`**
```ini
[flake8]
max-line-length = 100
exclude =
    .git,
    __pycache__,
    */migrations/*,
    .venv,
    build,
    dist
ignore = E203, E266, W503
max-complexity = 10
```

**Task 0.4.3: Configure Pre-commit Hooks** (1 hour)

**File: `.pre-commit-config.yaml`**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        exclude: ^migrations/
```

```bash
# Install hooks
pre-commit install
```

#### Day 5: Documentation & Baseline Metrics

**Task 0.5.1: Generate Code Metrics Baseline** (2 hours)

**File: `C:\Users\alvarosps\git\condominios_manager\scripts\generate_metrics.py`**
```python
"""
Generate code quality metrics baseline
Usage: python scripts/generate_metrics.py
"""
import subprocess
from pathlib import Path
from datetime import datetime

def run_command(cmd, description):
    """Run shell command and capture output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def generate_metrics():
    """Generate all metrics"""
    metrics_dir = Path(__file__).parent.parent / 'metrics'
    metrics_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = metrics_dir / f'baseline_metrics_{timestamp}.txt'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"Code Quality Metrics - Baseline Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"{'='*80}\n\n")

        # Lines of code
        output = run_command('cloc core --exclude-dir=migrations', 'Lines of Code (CLOC)')
        f.write(output + '\n\n')

        # Flake8 violations
        output = run_command('flake8 core --count', 'Flake8 Violations')
        f.write(output + '\n\n')

        # Pylint score
        output = run_command('pylint core --exit-zero', 'Pylint Analysis')
        f.write(output + '\n\n')

        # Bandit security issues
        output = run_command('bandit -r core -f txt', 'Security Analysis (Bandit)')
        f.write(output + '\n\n')

        # Complexity analysis
        output = run_command('radon cc core -a -nb', 'Cyclomatic Complexity')
        f.write(output + '\n\n')

        # Maintainability index
        output = run_command('radon mi core -nb', 'Maintainability Index')
        f.write(output + '\n\n')

    print(f"\n✓ Metrics report generated: {report_file}")
    return report_file

if __name__ == '__main__':
    # Install required tools if not present
    subprocess.run('pip install cloc radon bandit', shell=True)
    generate_metrics()
```

**Task 0.5.2: Create Current Architecture Diagram** (2 hours)

**File: `docs/architecture/current_state.md`**
```markdown
# Current Architecture - Before Refactoring

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Application                       │
│                    (Monolithic Architecture)                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐      ┌──────────────┐      ┌────────────┐ │
│  │   ViewSets  │─────▶│ Serializers  │─────▶│   Models   │ │
│  │ (Business   │      │ (Validation  │      │  (Domain   │ │
│  │  Logic)     │      │  & Nested    │      │   & Data)  │ │
│  └─────────────┘      │  Creation)   │      └────────────┘ │
│         │             └──────────────┘             │        │
│         │                                          │        │
│         ▼                                          ▼        │
│  ┌─────────────┐                           ┌────────────┐  │
│  │  PDF Gen    │                           │ PostgreSQL │  │
│  │ (Pyppeteer) │                           │  Database  │  │
│  └─────────────┘                           └────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Views (core/views.py)
- HTTP request handling
- Business logic (113-line generate_contract method)
- PDF generation orchestration
- Fee calculations
- Date arithmetic
- File system operations

### Serializers (core/serializers.py)
- Data validation
- Nested object creation (Tenant + Dependents)
- Many-to-many relationship handling
- Business logic (duplicate dependent deletion)

### Models (core/models.py)
- Data structure definition
- Database constraints
- Data redundancy (Apartment vs Lease fields)

### Utils (core/utils.py)
- Currency formatting
- Number to words conversion
- No error handling

## Critical Issues

1. **No Separation of Concerns**: All layers mixed together
2. **Fat Views**: 113-line generate_contract method
3. **Hardcoded Dependencies**: Chrome path, database credentials
4. **No Service Layer**: Business logic not reusable
5. **Data Redundancy**: Duplicate fields in models
6. **Zero Tests**: No test coverage
7. **No Type Hints**: Poor IDE support and type safety
8. **Poor Error Handling**: Generic exceptions, print statements
```

**Task 0.5.3: Document Current API Contract** (2 hours)

**File: `docs/api/current_endpoints.md`**
```markdown
# Current API Endpoints - Baseline

## Buildings
- `GET /api/buildings/` - List all buildings
- `POST /api/buildings/` - Create building
- `GET /api/buildings/{id}/` - Retrieve building
- `PUT /api/buildings/{id}/` - Update building
- `PATCH /api/buildings/{id}/` - Partial update
- `DELETE /api/buildings/{id}/` - Delete building

## Apartments
- `GET /api/apartments/` - List all apartments
- `POST /api/apartments/` - Create apartment
- `GET /api/apartments/{id}/` - Retrieve apartment
- `PUT /api/apartments/{id}/` - Update apartment
- `PATCH /api/apartments/{id}/` - Partial update
- `DELETE /api/apartments/{id}/` - Delete apartment

## Tenants
- `GET /api/tenants/` - List all tenants
- `POST /api/tenants/` - Create tenant (with dependents)
- `GET /api/tenants/{id}/` - Retrieve tenant
- `PUT /api/tenants/{id}/` - Update tenant
- `PATCH /api/tenants/{id}/` - Partial update
- `DELETE /api/tenants/{id}/` - Delete tenant

## Leases
- `GET /api/leases/` - List all leases
- `POST /api/leases/` - Create lease
- `GET /api/leases/{id}/` - Retrieve lease
- `PUT /api/leases/{id}/` - Update lease
- `PATCH /api/leases/{id}/` - Partial update
- `DELETE /api/leases/{id}/` - Delete lease
- `POST /api/leases/{id}/generate_contract/` - Generate PDF contract
- `GET /api/leases/{id}/calculate_late_fee/` - Calculate late fee
- `POST /api/leases/{id}/change_due_date/` - Change due date

## Furnitures
- `GET /api/furnitures/` - List all furnitures
- `POST /api/furnitures/` - Create furniture
- `GET /api/furnitures/{id}/` - Retrieve furniture
- `PUT /api/furnitures/{id}/` - Update furniture
- `PATCH /api/furnitures/{id}/` - Partial update
- `DELETE /api/furnitures/{id}/` - Delete furniture

## Request/Response Examples

### Create Lease
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

### Generate Contract
```json
POST /api/leases/1/generate_contract/

Response:
{
  "message": "Contrato gerado com sucesso!",
  "pdf_path": "C:\\path\\to\\contracts\\836\\contract_apto_102_1.pdf"
}
```

**CRITICAL**: These endpoints MUST remain functional and backward-compatible throughout refactoring.
```

### Deliverables

- [ ] Development branch created
- [ ] Branching strategy documented
- [ ] Git hooks configured
- [ ] `.env.example` created
- [ ] Environment configuration implemented
- [ ] Database backup scripts created
- [ ] Initial database backup taken
- [ ] Code quality tools installed and configured
- [ ] Pre-commit hooks active
- [ ] Baseline metrics report generated
- [ ] Current architecture documented
- [ ] API contract documented

### Success Criteria

- ✅ All developers can set up environment from `.env.example`
- ✅ Database can be backed up and restored successfully
- ✅ Pre-commit hooks run on every commit
- ✅ Baseline metrics captured for comparison
- ✅ Documentation exists for current state

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Environment differences | Medium | Low | Standardized .env configuration |
| Backup failures | Low | High | Test restore immediately after backup |
| Tool incompatibilities | Low | Low | Use specific version pins |

### Rollback Strategy

- Remove pre-commit hooks: `pre-commit uninstall`
- Revert settings.py changes
- Continue with hardcoded configuration

---

## Phase 1: Foundation & Testing Infrastructure

**Duration:** 2 weeks (10 days)
**Priority:** Critical
**Risk:** Low
**Dependencies:** Phase 0 complete

### Objectives

- Establish comprehensive test coverage (target: 60%+)
- Create test fixtures and factories
- Implement CI/CD pipeline
- Add type hints to existing code
- Set up logging infrastructure

### Week 1: Testing Framework & Initial Coverage

#### Day 1: pytest Setup & Configuration

**Task 1.1.1: Install Testing Dependencies** (1 hour)
```bash
pip install pytest pytest-django pytest-cov pytest-mock factory-boy faker freezegun
pip install pytest-xdist  # For parallel test execution
pip freeze > requirements-dev.txt
```

**Task 1.1.2: Configure pytest** (2 hours)

**File: `pytest.ini`**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = condominios_manager.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --cov=core
    --cov-report=html
    --cov-report=term-missing:skip-covered
    --cov-fail-under=60
    -v
    --tb=short
    --maxfail=1
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    unit: marks tests as unit tests
    integration: marks tests as integration tests
    pdf: marks tests that generate PDFs
testpaths = tests
```

**File: `conftest.py`**
```python
"""
PyTest configuration and shared fixtures
"""
import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.fixture(scope='session')
def django_db_setup():
    """Use test database for all tests"""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'condominio_test',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }


@pytest.fixture
def api_client():
    """Return API client for testing"""
    return APIClient()


@pytest.fixture
def test_settings():
    """Override settings for tests"""
    with override_settings(
        DEBUG=False,
        CHROME_EXECUTABLE_PATH='mock_chrome_path',
        PDF_OUTPUT_DIR='test_contracts',
    ):
        yield


@pytest.fixture(autouse=True)
def cleanup_test_files(tmp_path):
    """Cleanup temporary files after each test"""
    yield
    # Cleanup logic here if needed
```

**Task 1.1.3: Create Test Directory Structure** (1 hour)
```bash
mkdir tests
mkdir tests\unit
mkdir tests\integration
mkdir tests\fixtures
```

**File: `tests\__init__.py`**
```python
"""Test package initialization"""
```

#### Day 2-3: Model Tests & Factories

**Task 1.2.1: Create Model Factories** (4 hours)

**File: `tests\fixtures\factories.py`**
```python
"""
Factory classes for creating test data
"""
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from datetime import date, timedelta

from core.models import Building, Apartment, Furniture, Tenant, Dependent, Lease

fake = Faker('pt_BR')


class BuildingFactory(DjangoModelFactory):
    """Factory for Building model"""

    class Meta:
        model = Building

    street_number = factory.Sequence(lambda n: 800 + n)
    name = factory.LazyAttribute(lambda obj: f"Edifício {obj.street_number}")
    address = factory.Faker('address', locale='pt_BR')


class FurnitureFactory(DjangoModelFactory):
    """Factory for Furniture model"""

    class Meta:
        model = Furniture

    name = factory.Iterator([
        'Fogão', 'Geladeira', 'Micro-ondas', 'Sofá',
        'Mesa', 'Cadeira', 'Cama', 'Guarda-roupa'
    ])
    description = factory.Faker('sentence', locale='pt_BR')


class ApartmentFactory(DjangoModelFactory):
    """Factory for Apartment model"""

    class Meta:
        model = Apartment

    building = factory.SubFactory(BuildingFactory)
    number = factory.Sequence(lambda n: 100 + n)
    interfone_configured = False
    contract_generated = False
    contract_signed = False
    rental_value = Decimal('1500.00')
    cleaning_fee = Decimal('200.00')
    max_tenants = 2
    is_rented = False
    lease_date = None
    last_rent_increase_date = None

    @factory.post_generation
    def furnitures(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for furniture in extracted:
                self.furnitures.add(furniture)


class TenantFactory(DjangoModelFactory):
    """Factory for Tenant model"""

    class Meta:
        model = Tenant

    name = factory.Faker('name', locale='pt_BR')
    cpf_cnpj = factory.Sequence(lambda n: f"{n:011d}")
    is_company = False
    rg = factory.Sequence(lambda n: f"{n:09d}")
    phone = factory.Faker('phone_number', locale='pt_BR')
    marital_status = factory.Iterator(['Solteiro', 'Casado', 'Divorciado', 'Viúvo'])
    profession = factory.Faker('job', locale='pt_BR')
    deposit_amount = Decimal('1500.00')
    cleaning_fee_paid = False
    tag_deposit_paid = False
    rent_due_day = 10

    @factory.post_generation
    def furnitures(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for furniture in extracted:
                self.furnitures.add(furniture)


class DependentFactory(DjangoModelFactory):
    """Factory for Dependent model"""

    class Meta:
        model = Dependent

    tenant = factory.SubFactory(TenantFactory)
    name = factory.Faker('name', locale='pt_BR')
    phone = factory.Faker('phone_number', locale='pt_BR')


class LeaseFactory(DjangoModelFactory):
    """Factory for Lease model"""

    class Meta:
        model = Lease

    apartment = factory.SubFactory(ApartmentFactory)
    responsible_tenant = factory.SubFactory(TenantFactory)
    number_of_tenants = 1
    start_date = factory.LazyFunction(lambda: date.today())
    validity_months = 12
    due_day = 10
    rental_value = Decimal('1500.00')
    cleaning_fee = Decimal('200.00')
    tag_fee = Decimal('50.00')
    contract_generated = False
    contract_signed = False
    interfone_configured = False
    warning_count = 0

    @factory.post_generation
    def tenants(self, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            self.tenants.add(self.responsible_tenant)
        else:
            for tenant in extracted:
                self.tenants.add(tenant)
```

**Task 1.2.2: Create Model Unit Tests** (6 hours)

**File: `tests\unit\test_models.py`**
```python
"""
Unit tests for Django models
"""
import pytest
from decimal import Decimal
from datetime import date
from django.db import IntegrityError

from core.models import Building, Apartment, Furniture, Tenant, Dependent, Lease
from tests.fixtures.factories import (
    BuildingFactory, ApartmentFactory, FurnitureFactory,
    TenantFactory, DependentFactory, LeaseFactory
)


@pytest.mark.django_db
class TestBuildingModel:
    """Test Building model"""

    def test_create_building(self):
        """Test building creation"""
        building = BuildingFactory(street_number=836, name="Edifício 836")
        assert building.street_number == 836
        assert building.name == "Edifício 836"
        assert str(building) == "Edifício 836 - 836"

    def test_street_number_unique(self):
        """Test street_number uniqueness constraint"""
        BuildingFactory(street_number=836)
        with pytest.raises(IntegrityError):
            BuildingFactory(street_number=836)

    def test_building_apartments_relationship(self):
        """Test building to apartments relationship"""
        building = BuildingFactory()
        apt1 = ApartmentFactory(building=building, number=101)
        apt2 = ApartmentFactory(building=building, number=102)

        assert building.apartments.count() == 2
        assert apt1 in building.apartments.all()
        assert apt2 in building.apartments.all()


@pytest.mark.django_db
class TestApartmentModel:
    """Test Apartment model"""

    def test_create_apartment(self):
        """Test apartment creation"""
        building = BuildingFactory()
        apartment = ApartmentFactory(
            building=building,
            number=102,
            rental_value=Decimal('1500.00')
        )
        assert apartment.number == 102
        assert apartment.rental_value == Decimal('1500.00')
        assert str(apartment) == f"Apto 102 - {building.street_number}"

    def test_apartment_unique_together(self):
        """Test unique_together constraint (building, number)"""
        building = BuildingFactory()
        ApartmentFactory(building=building, number=102)

        with pytest.raises(IntegrityError):
            ApartmentFactory(building=building, number=102)

    def test_apartment_different_buildings_same_number(self):
        """Test same number allowed in different buildings"""
        building1 = BuildingFactory(street_number=836)
        building2 = BuildingFactory(street_number=850)

        apt1 = ApartmentFactory(building=building1, number=102)
        apt2 = ApartmentFactory(building=building2, number=102)

        assert apt1.number == apt2.number
        assert apt1.building != apt2.building

    def test_apartment_furnitures_relationship(self):
        """Test apartment to furnitures many-to-many"""
        furniture1 = FurnitureFactory(name="Fogão")
        furniture2 = FurnitureFactory(name="Geladeira")
        apartment = ApartmentFactory(furnitures=[furniture1, furniture2])

        assert apartment.furnitures.count() == 2
        assert furniture1 in apartment.furnitures.all()


@pytest.mark.django_db
class TestTenantModel:
    """Test Tenant model"""

    def test_create_tenant(self):
        """Test tenant creation"""
        tenant = TenantFactory(
            name="João Silva",
            cpf_cnpj="12345678901",
            marital_status="Casado"
        )
        assert tenant.name == "João Silva"
        assert tenant.cpf_cnpj == "12345678901"
        assert str(tenant) == "João Silva"

    def test_cpf_cnpj_unique(self):
        """Test CPF/CNPJ uniqueness constraint"""
        TenantFactory(cpf_cnpj="12345678901")
        with pytest.raises(IntegrityError):
            TenantFactory(cpf_cnpj="12345678901")

    def test_tenant_dependents_relationship(self):
        """Test tenant to dependents relationship"""
        tenant = TenantFactory()
        dep1 = DependentFactory(tenant=tenant, name="Maria Silva")
        dep2 = DependentFactory(tenant=tenant, name="Pedro Silva")

        assert tenant.dependents.count() == 2
        assert dep1 in tenant.dependents.all()


@pytest.mark.django_db
class TestLeaseModel:
    """Test Lease model"""

    def test_create_lease(self):
        """Test lease creation"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 15),
            validity_months=12
        )

        assert lease.apartment == apartment
        assert lease.responsible_tenant == tenant
        assert lease.validity_months == 12

    def test_lease_one_to_one_apartment(self):
        """Test OneToOne relationship with apartment"""
        apartment = ApartmentFactory()
        LeaseFactory(apartment=apartment)

        with pytest.raises(IntegrityError):
            LeaseFactory(apartment=apartment)

    def test_lease_multiple_tenants(self):
        """Test many-to-many relationship with tenants"""
        tenant1 = TenantFactory()
        tenant2 = TenantFactory()
        lease = LeaseFactory(
            responsible_tenant=tenant1,
            tenants=[tenant1, tenant2]
        )

        assert lease.tenants.count() == 2
        assert tenant1 in lease.tenants.all()
        assert tenant2 in lease.tenants.all()
```

#### Day 4-5: Serializer and View Tests

**Task 1.3.1: Create Serializer Tests** (6 hours)

**File: `tests\unit\test_serializers.py`**
```python
"""
Unit tests for DRF serializers
"""
import pytest
from decimal import Decimal
from datetime import date

from core.serializers import (
    BuildingSerializer, ApartmentSerializer, TenantSerializer,
    LeaseSerializer, FurnitureSerializer
)
from tests.fixtures.factories import (
    BuildingFactory, ApartmentFactory, TenantFactory,
    LeaseFactory, FurnitureFactory
)


@pytest.mark.django_db
class TestBuildingSerializer:
    """Test BuildingSerializer"""

    def test_serialize_building(self):
        """Test serialization"""
        building = BuildingFactory(street_number=836, name="Edifício 836")
        serializer = BuildingSerializer(building)

        assert serializer.data['street_number'] == 836
        assert serializer.data['name'] == "Edifício 836"

    def test_deserialize_building(self):
        """Test deserialization and validation"""
        data = {
            'street_number': 836,
            'name': 'Edifício 836',
            'address': 'Rua Teste, 836'
        }
        serializer = BuildingSerializer(data=data)

        assert serializer.is_valid()
        building = serializer.save()
        assert building.street_number == 836


@pytest.mark.django_db
class TestTenantSerializer:
    """Test TenantSerializer"""

    def test_serialize_tenant_with_dependents(self):
        """Test serialization with nested dependents"""
        tenant = TenantFactory()
        tenant.dependents.create(name="Dependent 1", phone="11999999999")
        tenant.dependents.create(name="Dependent 2", phone="11988888888")

        serializer = TenantSerializer(tenant)

        assert len(serializer.data['dependents']) == 2
        assert serializer.data['dependents'][0]['name'] == "Dependent 1"

    def test_create_tenant_with_dependents(self):
        """Test nested creation of tenant with dependents"""
        furniture = FurnitureFactory()
        data = {
            'name': 'João Silva',
            'cpf_cnpj': '12345678901',
            'phone': '11999999999',
            'marital_status': 'Casado',
            'profession': 'Engenheiro',
            'furniture_ids': [furniture.id],
            'dependents': [
                {'name': 'Maria Silva', 'phone': '11988888888'},
                {'name': 'Pedro Silva', 'phone': '11977777777'}
            ]
        }

        serializer = TenantSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        tenant = serializer.save()
        assert tenant.dependents.count() == 2
        assert tenant.furnitures.count() == 1


@pytest.mark.django_db
class TestLeaseSerializer:
    """Test LeaseSerializer"""

    def test_serialize_lease(self):
        """Test lease serialization with nested objects"""
        lease = LeaseFactory()
        serializer = LeaseSerializer(lease)

        assert 'apartment' in serializer.data
        assert 'responsible_tenant' in serializer.data
        assert serializer.data['rental_value'] == '1500.00'

    def test_create_lease(self):
        """Test lease creation via serializer"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        data = {
            'apartment_id': apartment.id,
            'responsible_tenant_id': tenant.id,
            'tenant_ids': [tenant.id],
            'start_date': '2025-01-15',
            'validity_months': 12,
            'due_day': 10,
            'rental_value': '1500.00',
            'cleaning_fee': '200.00',
            'tag_fee': '50.00'
        }

        serializer = LeaseSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        lease = serializer.save()
        assert lease.apartment == apartment
        assert lease.responsible_tenant == tenant
```

**Task 1.3.2: Create API View Tests** (6 hours)

**File: `tests\integration\test_api_views.py`**
```python
"""
Integration tests for API views
"""
import pytest
from rest_framework import status
from django.urls import reverse

from core.models import Building, Apartment, Tenant, Lease
from tests.fixtures.factories import (
    BuildingFactory, ApartmentFactory, TenantFactory, LeaseFactory
)


@pytest.mark.django_db
class TestBuildingAPI:
    """Test Building API endpoints"""

    def test_list_buildings(self, api_client):
        """Test GET /api/buildings/"""
        BuildingFactory.create_batch(3)

        url = reverse('building-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_create_building(self, api_client):
        """Test POST /api/buildings/"""
        data = {
            'street_number': 836,
            'name': 'Edifício 836',
            'address': 'Rua Teste, 836'
        }

        url = reverse('building-list')
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Building.objects.count() == 1
        assert Building.objects.first().street_number == 836

    def test_retrieve_building(self, api_client):
        """Test GET /api/buildings/{id}/"""
        building = BuildingFactory()

        url = reverse('building-detail', args=[building.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == building.id


@pytest.mark.django_db
class TestLeaseAPI:
    """Test Lease API endpoints"""

    def test_create_lease(self, api_client):
        """Test POST /api/leases/"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        data = {
            'apartment_id': apartment.id,
            'responsible_tenant_id': tenant.id,
            'tenant_ids': [tenant.id],
            'start_date': '2025-01-15',
            'validity_months': 12,
            'due_day': 10,
            'rental_value': '1500.00',
            'cleaning_fee': '200.00',
            'tag_fee': '50.00'
        }

        url = reverse('lease-list')
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Lease.objects.count() == 1

    @pytest.mark.pdf
    def test_generate_contract_endpoint(self, api_client, mocker):
        """Test POST /api/leases/{id}/generate_contract/"""
        lease = LeaseFactory()

        # Mock PDF generation to avoid actual Chrome execution
        mock_pdf = mocker.patch('core.views.asyncio.run')

        url = reverse('lease-generate-contract', args=[lease.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'pdf_path' in response.data
        assert mock_pdf.called

    def test_calculate_late_fee(self, api_client):
        """Test GET /api/leases/{id}/calculate_late_fee/"""
        lease = LeaseFactory(due_day=5)

        url = reverse('lease-calculate-late-fee', args=[lease.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response varies based on current date

    def test_change_due_date(self, api_client):
        """Test POST /api/leases/{id}/change_due_date/"""
        lease = LeaseFactory(due_day=10)

        url = reverse('lease-change-due-date', args=[lease.id])
        response = api_client.post(url, {'new_due_day': 15})

        assert response.status_code == status.HTTP_200_OK
        lease.refresh_from_db()
        assert lease.due_day == 15
        assert 'fee' in response.data
```

### Week 2: Type Hints, Logging, and CI/CD

#### Day 6-7: Add Type Hints

**Task 1.4.1: Add Type Hints to Models** (4 hours)

**File: `core\models.py`** (partial update with type hints)
```python
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from typing import Optional
from datetime import date as DateType


class Building(models.Model):
    """
    Represents a building in the condominium system.

    Attributes:
        street_number: Unique street number identifier (e.g., 836, 850)
        name: Building name
        address: Full address of the building
    """
    street_number: int = models.PositiveIntegerField(
        unique=True,
        help_text="Número da rua (ex.: 836 ou 850)"
    )
    name: str = models.CharField(
        max_length=100,
        help_text="Nome do prédio"
    )
    address: str = models.CharField(
        max_length=200,
        help_text="Endereço completo do prédio"
    )

    def __str__(self) -> str:
        return f"{self.name} - {self.street_number}"


class Apartment(models.Model):
    """
    Represents an apartment unit within a building.

    Attributes:
        building: Foreign key to Building
        number: Apartment number within the building
        rental_value: Monthly rental price
        cleaning_fee: One-time cleaning fee
        max_tenants: Maximum number of allowed tenants
        is_rented: Whether apartment is currently rented
        lease_date: Date when current lease started
        last_rent_increase_date: Date of last rent increase
    """
    building: Building
    number: int
    interfone_configured: bool
    contract_generated: bool
    contract_signed: bool
    rental_value: Decimal
    cleaning_fee: Decimal
    max_tenants: int
    is_rented: bool
    lease_date: Optional[DateType]
    last_rent_increase_date: Optional[DateType]

    # ... (rest of model definition)
```

**Task 1.4.2: Add Type Hints to Views** (4 hours)

**File: `core\views.py`** (partial update with type hints)
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from typing import Dict, Any, Optional
from django.db.models import QuerySet

from .models import Building, Furniture, Apartment, Tenant, Lease
from .serializers import (
    BuildingSerializer, FurnitureSerializer, ApartmentSerializer,
    TenantSerializer, LeaseSerializer
)


class BuildingViewSet(viewsets.ModelViewSet):
    """ViewSet for Building CRUD operations"""
    queryset: QuerySet[Building] = Building.objects.all()
    serializer_class = BuildingSerializer


class LeaseViewSet(viewsets.ModelViewSet):
    """ViewSet for Lease CRUD operations and special actions"""
    queryset: QuerySet[Lease] = Lease.objects.all()
    serializer_class = LeaseSerializer

    @action(detail=True, methods=['post'])
    def generate_contract(self, request: Request, pk: Optional[int] = None) -> Response:
        """
        Generate PDF contract for a lease.

        Args:
            request: HTTP request object
            pk: Primary key of the lease

        Returns:
            Response with success message and PDF path, or error message
        """
        lease: Lease = self.get_object()
        # ... implementation
```

**Task 1.4.3: Add Type Hints to Utils** (2 hours)

**File: `core\utils.py`** (complete rewrite with type hints)
```python
"""
Utility functions for the core application.
"""
from typing import Union
from decimal import Decimal
from num2words import num2words
import logging

logger = logging.getLogger(__name__)


def number_to_words(value: Union[int, float, Decimal, str]) -> str:
    """
    Convert a numeric value to words in Brazilian Portuguese.

    Args:
        value: Numeric value to convert

    Returns:
        String representation of the number in words

    Examples:
        >>> number_to_words(1500)
        'mil e quinhentos'
        >>> number_to_words(1500.50)
        'mil, quinhentos e cinquenta centavos'
    """
    try:
        numeric_value = float(value)
        return num2words(numeric_value, lang='pt_BR')
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting {value} to words: {e}")
        return str(value)


def format_currency(value: Union[int, float, Decimal]) -> str:
    """
    Format a numeric value as Brazilian Real currency.

    Args:
        value: Numeric value to format

    Returns:
        Formatted currency string (e.g., "R$1.500,00")

    Examples:
        >>> format_currency(1500)
        'R$1.500,00'
        >>> format_currency(1500.50)
        'R$1.500,50'
    """
    try:
        # Brazilian format: R$1.500,50
        formatted = f"R${value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting {value} as currency: {e}")
        return f"R${value}"
```

#### Day 8: Logging Infrastructure

**Task 1.5.1: Configure Logging** (3 hours)

**File: `condominios_manager\settings.py`** (add logging configuration)
```python
# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module}.{funcName}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Create logs directory
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
```

**Task 1.5.2: Add Logging to Views** (3 hours)

**File: `core\views.py`** (add logging)
```python
import logging

logger = logging.getLogger(__name__)


class LeaseViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @action(detail=True, methods=['post'])
    def generate_contract(self, request: Request, pk: Optional[int] = None) -> Response:
        """Generate PDF contract for a lease"""
        lease: Lease = self.get_object()
        logger.info(f"Starting contract generation for Lease #{lease.id}")

        try:
            # ... existing implementation ...
            logger.info(f"Contract generated successfully for Lease #{lease.id}: {pdf_path}")
            return Response(
                {"message": "Contrato gerado com sucesso!", "pdf_path": pdf_path},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Contract generation failed for Lease #{lease.id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "Erro ao gerar contrato. Verifique os logs para mais detalhes."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

#### Day 9-10: CI/CD Pipeline

**Task 1.6.1: Create GitHub Actions Workflow** (4 hours)

**File: `.github\workflows\ci.yml`**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ master, develop, 'refactoring/**' ]
  pull_request:
    branches: [ master, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: condominio_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run linters
      run: |
        black --check core
        isort --check-only core
        flake8 core
        pylint core --exit-zero

    - name: Run type checking
      run: |
        mypy core --ignore-missing-imports

    - name: Run security checks
      run: |
        bandit -r core -ll
        safety check

    - name: Run tests with coverage
      env:
        DB_NAME: condominio_test
        DB_USER: postgres
        DB_PASSWORD: postgres
        DB_HOST: localhost
        DB_PORT: 5432
        SECRET_KEY: test-secret-key
      run: |
        pytest --cov=core --cov-report=xml --cov-report=html

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: false

  build:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/master'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image (future)
      run: echo "Docker build will be implemented in Phase 4"
```

**Task 1.6.2: Create Docker Development Environment** (4 hours)

**File: `Dockerfile.dev`**
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**File: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: condominio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    environment:
      - DB_NAME=condominio
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - DB_HOST=db
      - DB_PORT=5432
      - DEBUG=True
      - CHROME_EXECUTABLE_PATH=/usr/bin/chromium
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

### Deliverables

- [ ] pytest configured with 60%+ coverage requirement
- [ ] Model factories created for all models
- [ ] Unit tests for models (100% coverage)
- [ ] Unit tests for serializers (80%+ coverage)
- [ ] Integration tests for API views (80%+ coverage)
- [ ] Type hints added to all modules
- [ ] Logging infrastructure implemented
- [ ] CI/CD pipeline active on GitHub Actions
- [ ] Docker development environment configured

### Success Criteria

- ✅ `pytest` passes with 60%+ code coverage
- ✅ All pre-commit hooks pass
- ✅ CI/CD pipeline passes on all branches
- ✅ `mypy` type checking passes (with ignoring missing imports)
- ✅ Logs directory created and logs being written
- ✅ Docker compose starts successfully

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| PDF tests failing in CI | High | Medium | Mock pyppeteer, use @pytest.mark.pdf to skip |
| Low initial coverage | Medium | Low | Incremental improvement, start with 60% target |
| Type hint errors | Medium | Low | Use gradual typing, ignore missing imports |
| CI pipeline slow | Medium | Low | Use caching, parallel test execution |

### Rollback Strategy

- Remove pytest configuration, continue manual testing
- Disable pre-commit hooks if blocking development
- Revert type hints if causing issues
- Skip CI/CD, deploy manually

---

## Phase 2: Service Layer Extraction

**Duration:** 3 weeks (15 days)
**Priority:** Critical
**Risk:** Medium
**Dependencies:** Phase 1 complete

### Objectives

- Extract business logic from views into service layer
- Implement dependency injection for testability
- Create domain services for complex operations
- Maintain 100% backward compatibility with existing APIs

### Week 1: Service Layer Foundation

#### Day 1-2: Create Service Layer Structure

**Task 2.1.1: Create Service Layer Directory** (2 hours)

```bash
mkdir core\services
mkdir core\services\__init__.py
```

**File: `core\services\__init__.py`**
```python
"""
Service layer for business logic.

This package contains service classes that encapsulate business logic
previously embedded in views and serializers.
"""
from .lease_service import LeaseService
from .contract_service import ContractService
from .fee_calculator_service import FeeCalculatorService

__all__ = [
    'LeaseService',
    'ContractService',
    'FeeCalculatorService',
]
```

**Task 2.1.2: Create Base Service Class** (2 hours)

**File: `core\services\base.py`**
```python
"""
Base service class for common service functionality.
"""
from typing import Generic, TypeVar, Type, Optional, List
from django.db.models import Model, QuerySet
import logging

ModelType = TypeVar('ModelType', bound=Model)


class BaseService(Generic[ModelType]):
    """
    Base service class providing common CRUD operations.

    Attributes:
        model: The Django model class this service operates on
        logger: Logger instance for this service
    """

    model: Type[ModelType]

    def __init__(self):
        """Initialize service with model and logger"""
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_queryset(self) -> QuerySet[ModelType]:
        """
        Get the base queryset for this service.

        Returns:
            QuerySet for the model
        """
        return self.model.objects.all()

    def get_by_id(self, pk: int) -> Optional[ModelType]:
        """
        Retrieve an object by its primary key.

        Args:
            pk: Primary key of the object

        Returns:
            Model instance if found, None otherwise
        """
        try:
            return self.get_queryset().get(pk=pk)
        except self.model.DoesNotExist:
            self.logger.warning(f"{self.model.__name__} with id {pk} not found")
            return None

    def get_all(self) -> List[ModelType]:
        """
        Get all objects.

        Returns:
            List of all model instances
        """
        return list(self.get_queryset())

    def create(self, **kwargs) -> ModelType:
        """
        Create a new object.

        Args:
            **kwargs: Field values for the new object

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        instance.save()
        self.logger.info(f"Created {self.model.__name__} with id {instance.pk}")
        return instance

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """
        Update an existing object.

        Args:
            instance: Model instance to update
            **kwargs: Field values to update

        Returns:
            Updated model instance
        """
        for field, value in kwargs.items():
            setattr(instance, field, value)
        instance.save()
        self.logger.info(f"Updated {self.model.__name__} with id {instance.pk}")
        return instance

    def delete(self, instance: ModelType) -> None:
        """
        Delete an object.

        Args:
            instance: Model instance to delete
        """
        pk = instance.pk
        instance.delete()
        self.logger.info(f"Deleted {self.model.__name__} with id {pk}")
```

#### Day 3-5: Extract Fee Calculation Logic

**Task 2.2.1: Create FeeCalculatorService** (6 hours)

**File: `core\services\fee_calculator_service.py`**
```python
"""
Service for calculating fees related to leases.
"""
from decimal import Decimal
from datetime import date
from typing import Dict, Any
import logging

from core.models import Lease

logger = logging.getLogger(__name__)


class FeeCalculatorService:
    """
    Service for calculating various fees in the lease system.

    This service encapsulates all fee calculation logic, making it
    reusable across the application and easier to test.
    """

    # Constants (can be moved to settings)
    DAYS_PER_MONTH = 30
    LATE_FEE_PERCENTAGE = Decimal('0.05')  # 5% per day
    TAG_FEE_SINGLE_TENANT = Decimal('50.00')
    TAG_FEE_MULTIPLE_TENANTS = Decimal('80.00')

    @classmethod
    def calculate_daily_rate(cls, rental_value: Decimal) -> Decimal:
        """
        Calculate daily rental rate.

        Args:
            rental_value: Monthly rental value

        Returns:
            Daily rental rate

        Example:
            >>> FeeCalculatorService.calculate_daily_rate(Decimal('1500.00'))
            Decimal('50.00')
        """
        return rental_value / cls.DAYS_PER_MONTH

    @classmethod
    def calculate_late_fee(
        cls,
        rental_value: Decimal,
        due_day: int,
        current_date: date = None
    ) -> Dict[str, Any]:
        """
        Calculate late payment fee based on number of days overdue.

        Args:
            rental_value: Monthly rental value
            due_day: Day of month when payment is due (1-31)
            current_date: Date to calculate from (defaults to today)

        Returns:
            Dictionary with 'late_days' and 'late_fee' keys

        Example:
            >>> FeeCalculatorService.calculate_late_fee(
            ...     Decimal('1500.00'),
            ...     due_day=5,
            ...     current_date=date(2025, 1, 15)
            ... )
            {'late_days': 10, 'late_fee': Decimal('25.00')}
        """
        if current_date is None:
            current_date = date.today()

        if current_date.day <= due_day:
            logger.info(f"Payment not late: current day {current_date.day}, due day {due_day}")
            return {
                'late_days': 0,
                'late_fee': Decimal('0.00'),
                'is_late': False
            }

        late_days = current_date.day - due_day
        daily_rate = cls.calculate_daily_rate(rental_value)
        late_fee = daily_rate * late_days * cls.LATE_FEE_PERCENTAGE

        logger.info(
            f"Late fee calculated: {late_days} days late, "
            f"daily rate {daily_rate}, fee {late_fee}"
        )

        return {
            'late_days': late_days,
            'late_fee': late_fee,
            'is_late': True
        }

    @classmethod
    def calculate_due_date_change_fee(
        cls,
        rental_value: Decimal,
        current_due_day: int,
        new_due_day: int
    ) -> Decimal:
        """
        Calculate fee for changing the due date.

        The fee is proportional to the number of days changed.

        Args:
            rental_value: Monthly rental value
            current_due_day: Current due day (1-31)
            new_due_day: New due day (1-31)

        Returns:
            Fee amount for changing due date

        Example:
            >>> FeeCalculatorService.calculate_due_date_change_fee(
            ...     Decimal('1500.00'),
            ...     current_due_day=10,
            ...     new_due_day=15
            ... )
            Decimal('250.00')  # 5 days * 50.00 daily rate
        """
        days_difference = abs(new_due_day - current_due_day)
        daily_rate = cls.calculate_daily_rate(rental_value)
        fee = daily_rate * days_difference

        logger.info(
            f"Due date change fee: {days_difference} days, "
            f"daily rate {daily_rate}, fee {fee}"
        )

        return fee

    @classmethod
    def calculate_tag_fee(cls, number_of_tenants: int) -> Decimal:
        """
        Calculate tag deposit fee based on number of tenants.

        Args:
            number_of_tenants: Number of tenants in the lease

        Returns:
            Tag fee amount

        Example:
            >>> FeeCalculatorService.calculate_tag_fee(1)
            Decimal('50.00')
            >>> FeeCalculatorService.calculate_tag_fee(2)
            Decimal('80.00')
        """
        if number_of_tenants == 1:
            fee = cls.TAG_FEE_SINGLE_TENANT
        else:
            fee = cls.TAG_FEE_MULTIPLE_TENANTS

        logger.debug(f"Tag fee for {number_of_tenants} tenants: {fee}")
        return fee

    @classmethod
    def calculate_total_initial_cost(
        cls,
        rental_value: Decimal,
        cleaning_fee: Decimal,
        number_of_tenants: int
    ) -> Dict[str, Decimal]:
        """
        Calculate total initial cost for a new lease.

        Args:
            rental_value: Monthly rental value
            cleaning_fee: One-time cleaning fee
            number_of_tenants: Number of tenants

        Returns:
            Dictionary with breakdown of costs

        Example:
            >>> FeeCalculatorService.calculate_total_initial_cost(
            ...     Decimal('1500.00'),
            ...     Decimal('200.00'),
            ...     2
            ... )
            {
                'rental_value': Decimal('1500.00'),
                'cleaning_fee': Decimal('200.00'),
                'tag_fee': Decimal('80.00'),
                'total': Decimal('1780.00')
            }
        """
        tag_fee = cls.calculate_tag_fee(number_of_tenants)
        total = rental_value + cleaning_fee + tag_fee

        return {
            'rental_value': rental_value,
            'cleaning_fee': cleaning_fee,
            'tag_fee': tag_fee,
            'total': total
        }
```

**Task 2.2.2: Create Tests for FeeCalculatorService** (4 hours)

**File: `tests\unit\test_services\test_fee_calculator_service.py`**
```python
"""
Unit tests for FeeCalculatorService
"""
import pytest
from decimal import Decimal
from datetime import date

from core.services.fee_calculator_service import FeeCalculatorService


class TestFeeCalculatorService:
    """Test FeeCalculatorService calculations"""

    def test_calculate_daily_rate(self):
        """Test daily rate calculation"""
        rental_value = Decimal('1500.00')
        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)

        assert daily_rate == Decimal('50.00')

    def test_calculate_late_fee_not_late(self):
        """Test late fee when payment is not late"""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('1500.00'),
            due_day=15,
            current_date=date(2025, 1, 10)
        )

        assert result['late_days'] == 0
        assert result['late_fee'] == Decimal('0.00')
        assert result['is_late'] is False

    def test_calculate_late_fee_late(self):
        """Test late fee calculation when payment is late"""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('1500.00'),
            due_day=5,
            current_date=date(2025, 1, 15)
        )

        # 10 days late * 50.00 daily rate * 0.05 = 25.00
        assert result['late_days'] == 10
        assert result['late_fee'] == Decimal('25.00')
        assert result['is_late'] is True

    def test_calculate_due_date_change_fee(self):
        """Test due date change fee calculation"""
        fee = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal('1500.00'),
            current_due_day=10,
            new_due_day=15
        )

        # 5 days difference * 50.00 daily rate = 250.00
        assert fee == Decimal('250.00')

    def test_calculate_tag_fee_single_tenant(self):
        """Test tag fee for single tenant"""
        fee = FeeCalculatorService.calculate_tag_fee(1)
        assert fee == Decimal('50.00')

    def test_calculate_tag_fee_multiple_tenants(self):
        """Test tag fee for multiple tenants"""
        fee = FeeCalculatorService.calculate_tag_fee(2)
        assert fee == Decimal('80.00')

        fee = FeeCalculatorService.calculate_tag_fee(3)
        assert fee == Decimal('80.00')

    def test_calculate_total_initial_cost(self):
        """Test total initial cost calculation"""
        result = FeeCalculatorService.calculate_total_initial_cost(
            rental_value=Decimal('1500.00'),
            cleaning_fee=Decimal('200.00'),
            number_of_tenants=2
        )

        assert result['rental_value'] == Decimal('1500.00')
        assert result['cleaning_fee'] == Decimal('200.00')
        assert result['tag_fee'] == Decimal('80.00')
        assert result['total'] == Decimal('1780.00')
```

### Week 2: Date Calculator and Contract Services

#### Day 6-7: Create Date Calculator Service

**Task 2.3.1: Create DateCalculatorService** (6 hours)

**File: `core\services\date_calculator_service.py`**
```python
"""
Service for date calculations in lease management.
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DateCalculatorService:
    """
    Service for handling date calculations in leases.

    Handles complex edge cases like leap years and month boundaries.
    """

    @classmethod
    def calculate_next_month_date(cls, start_date: date) -> date:
        """
        Calculate the date one month from start_date.

        Args:
            start_date: Starting date

        Returns:
            Date one month later

        Example:
            >>> DateCalculatorService.calculate_next_month_date(date(2025, 1, 15))
            datetime.date(2025, 2, 15)
            >>> DateCalculatorService.calculate_next_month_date(date(2024, 1, 31))
            datetime.date(2024, 2, 29)  # Leap year
        """
        next_month = start_date + relativedelta(months=1)
        logger.debug(f"Next month from {start_date}: {next_month}")
        return next_month

    @classmethod
    def calculate_final_date(cls, start_date: date, validity_months: int) -> date:
        """
        Calculate lease end date.

        Handles special case: if start_date is Feb 29 and calculated end is Feb 28,
        move to March 1.

        Args:
            start_date: Lease start date
            validity_months: Lease duration in months

        Returns:
            Lease end date

        Example:
            >>> DateCalculatorService.calculate_final_date(date(2024, 2, 29), 12)
            datetime.date(2025, 3, 1)  # Feb 29 -> Feb 28 -> March 1
            >>> DateCalculatorService.calculate_final_date(date(2025, 1, 15), 12)
            datetime.date(2026, 1, 15)
        """
        calculated_final = start_date + relativedelta(months=validity_months)

        # Special handling for Feb 29 -> Feb 28 edge case
        if start_date.month == 2 and start_date.day == 29:
            if calculated_final.month == 2 and calculated_final.day == 28:
                calculated_final = calculated_final + timedelta(days=1)
                logger.info(
                    f"Adjusted Feb 28 to March 1 for leap year edge case "
                    f"(start: {start_date})"
                )

        logger.info(
            f"Final date calculated: {start_date} + {validity_months} months = {calculated_final}"
        )
        return calculated_final

    @classmethod
    def calculate_lease_dates(
        cls,
        start_date: date,
        validity_months: int
    ) -> Dict[str, Any]:
        """
        Calculate all relevant dates for a lease.

        Args:
            start_date: Lease start date
            validity_months: Lease duration in months

        Returns:
            Dictionary with start_date, next_month_date, and final_date

        Example:
            >>> DateCalculatorService.calculate_lease_dates(
            ...     date(2025, 1, 15), 12
            ... )
            {
                'start_date': datetime.date(2025, 1, 15),
                'next_month_date': datetime.date(2025, 2, 15),
                'final_date': datetime.date(2026, 1, 15),
                'validity_months': 12
            }
        """
        next_month = cls.calculate_next_month_date(start_date)
        final_date = cls.calculate_final_date(start_date, validity_months)

        return {
            'start_date': start_date,
            'next_month_date': next_month,
            'final_date': final_date,
            'validity_months': validity_months
        }

    @classmethod
    def is_rent_due(cls, due_day: int, current_date: date = None) -> bool:
        """
        Check if rent is currently due.

        Args:
            due_day: Day of month when rent is due
            current_date: Date to check (defaults to today)

        Returns:
            True if rent is due, False otherwise
        """
        if current_date is None:
            current_date = date.today()

        return current_date.day >= due_day

    @classmethod
    def days_until_due(cls, due_day: int, current_date: date = None) -> int:
        """
        Calculate days until next rent due date.

        Args:
            due_day: Day of month when rent is due
            current_date: Date to check (defaults to today)

        Returns:
            Number of days until due date
        """
        if current_date is None:
            current_date = date.today()

        if current_date.day < due_day:
            return due_day - current_date.day
        else:
            # Next month's due date
            next_month = cls.calculate_next_month_date(current_date)
            next_due = date(next_month.year, next_month.month, due_day)
            return (next_due - current_date).days
```

**Task 2.3.2: Create Tests for DateCalculatorService** (4 hours)

**File: `tests\unit\test_services\test_date_calculator_service.py`**
```python
"""
Unit tests for DateCalculatorService
"""
import pytest
from datetime import date

from core.services.date_calculator_service import DateCalculatorService


class TestDateCalculatorService:
    """Test DateCalculatorService calculations"""

    def test_calculate_next_month_date_regular(self):
        """Test next month calculation for regular date"""
        result = DateCalculatorService.calculate_next_month_date(date(2025, 1, 15))
        assert result == date(2025, 2, 15)

    def test_calculate_next_month_date_month_end(self):
        """Test next month calculation for month-end date"""
        result = DateCalculatorService.calculate_next_month_date(date(2025, 1, 31))
        assert result == date(2025, 2, 28)  # Non-leap year

    def test_calculate_next_month_date_leap_year(self):
        """Test next month calculation for leap year"""
        result = DateCalculatorService.calculate_next_month_date(date(2024, 1, 31))
        assert result == date(2024, 2, 29)  # Leap year

    def test_calculate_final_date_regular(self):
        """Test final date calculation for regular case"""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 15), 12
        )
        assert result == date(2026, 1, 15)

    def test_calculate_final_date_leap_year_edge_case(self):
        """Test final date calculation for Feb 29 edge case"""
        # Feb 29, 2024 + 12 months = Feb 28, 2025 -> March 1, 2025
        result = DateCalculatorService.calculate_final_date(
            date(2024, 2, 29), 12
        )
        assert result == date(2025, 3, 1)

    def test_calculate_lease_dates(self):
        """Test comprehensive lease date calculation"""
        result = DateCalculatorService.calculate_lease_dates(
            date(2025, 1, 15), 12
        )

        assert result['start_date'] == date(2025, 1, 15)
        assert result['next_month_date'] == date(2025, 2, 15)
        assert result['final_date'] == date(2026, 1, 15)
        assert result['validity_months'] == 12

    def test_is_rent_due_not_due(self):
        """Test rent due check when not due"""
        result = DateCalculatorService.is_rent_due(
            due_day=15,
            current_date=date(2025, 1, 10)
        )
        assert result is False

    def test_is_rent_due_is_due(self):
        """Test rent due check when due"""
        result = DateCalculatorService.is_rent_due(
            due_day=10,
            current_date=date(2025, 1, 15)
        )
        assert result is True

    def test_days_until_due(self):
        """Test days until due calculation"""
        # Current day is 10, due day is 15 -> 5 days
        result = DateCalculatorService.days_until_due(
            due_day=15,
            current_date=date(2025, 1, 10)
        )
        assert result == 5
```

#### Day 8-10: Create Contract Service

**Task 2.4.1: Create ContractService** (8 hours)

**File: `core\services\contract_service.py`**
```python
"""
Service for contract generation and management.
"""
from typing import Dict, Any, List, Optional
from datetime import date
from pathlib import Path
import os
import asyncio
from decimal import Decimal

from django.conf import settings
from jinja2 import Environment, FileSystemLoader
from pyppeteer import launch

from core.models import Lease, Furniture
from core.services.date_calculator_service import DateCalculatorService
from core.services.fee_calculator_service import FeeCalculatorService
from core.utils import format_currency, number_to_words
from core.contract_rules import regras_condominio
import logging

logger = logging.getLogger(__name__)


class ContractGenerationError(Exception):
    """Exception raised when contract generation fails"""
    pass


class ContractService:
    """
    Service for generating lease contracts.

    This service handles PDF generation, template rendering,
    and contract data preparation.
    """

    def __init__(
        self,
        template_name: str = 'contract_template.html',
        chrome_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize contract service.

        Args:
            template_name: Name of the Jinja2 template file
            chrome_path: Path to Chrome executable (defaults to settings)
            output_dir: Directory for PDF output (defaults to settings)
        """
        self.template_name = template_name
        self.chrome_path = chrome_path or getattr(
            settings, 'CHROME_EXECUTABLE_PATH', None
        )
        self.output_dir = output_dir or getattr(
            settings, 'PDF_OUTPUT_DIR', 'contracts'
        )

        # Set up Jinja2 environment
        template_path = os.path.join(settings.BASE_DIR, 'core', 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path))
        self.jinja_env.filters['currency'] = format_currency
        self.jinja_env.filters['extenso'] = number_to_words

    def _calculate_lease_furnitures(self, lease: Lease) -> List[Furniture]:
        """
        Calculate which furniture items should appear in the contract.

        Contract furniture = Apartment furniture - Responsible tenant furniture

        Args:
            lease: Lease instance

        Returns:
            List of Furniture instances for the contract
        """
        apt_furniture = set(lease.apartment.furnitures.all())
        tenant_furniture = set(lease.responsible_tenant.furnitures.all())
        lease_furnitures = list(apt_furniture - tenant_furniture)

        logger.debug(
            f"Lease #{lease.id} furniture: {len(apt_furniture)} apt - "
            f"{len(tenant_furniture)} tenant = {len(lease_furnitures)} contract"
        )

        return lease_furnitures

    def prepare_contract_context(self, lease: Lease) -> Dict[str, Any]:
        """
        Prepare template context for contract generation.

        Args:
            lease: Lease instance

        Returns:
            Dictionary with all template variables
        """
        # Calculate dates
        dates = DateCalculatorService.calculate_lease_dates(
            lease.start_date,
            lease.validity_months
        )

        # Calculate costs
        tag_fee = FeeCalculatorService.calculate_tag_fee(
            len(lease.tenants.all())
        )
        total_cost = FeeCalculatorService.calculate_total_initial_cost(
            lease.rental_value,
            lease.cleaning_fee,
            len(lease.tenants.all())
        )

        # Get furniture
        furnitures = self._calculate_lease_furnitures(lease)

        context = {
            'tenant': lease.responsible_tenant,
            'building_number': lease.apartment.building.street_number,
            'apartment_number': lease.apartment.number,
            'furnitures': furnitures,
            'validity': lease.validity_months,
            'start_date': dates['start_date'].strftime("%d/%m/%Y"),
            'next_month_date': dates['next_month_date'].strftime("%d/%m/%Y"),
            'final_date': dates['final_date'].strftime("%d/%m/%Y"),
            'rental_value': lease.rental_value,
            'tag_fee': tag_fee,
            'cleaning_fee': lease.cleaning_fee,
            'valor_total': total_cost['total'],
            'valor_tags': tag_fee,
            'rules': regras_condominio,
            'lease': lease,
        }

        logger.debug(f"Prepared contract context for Lease #{lease.id}")
        return context

    def render_html(self, context: Dict[str, Any]) -> str:
        """
        Render HTML from template and context.

        Args:
            context: Template context dictionary

        Returns:
            Rendered HTML string
        """
        template = self.jinja_env.get_template(self.template_name)
        html_content = template.render(context)
        logger.debug(f"Rendered HTML template: {len(html_content)} characters")
        return html_content

    async def _generate_pdf_async(
        self,
        html_content: str,
        pdf_path: Path,
        temp_html_path: Path
    ) -> None:
        """
        Generate PDF using pyppeteer (async).

        Args:
            html_content: Rendered HTML string
            pdf_path: Path where PDF should be saved
            temp_html_path: Path for temporary HTML file
        """
        try:
            # Write temporary HTML file
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.debug(f"Launching Chrome: {self.chrome_path}")

            browser = await launch(
                handleSIGINT=False,
                handleSIGTERM=False,
                handleSIGHUP=False,
                options={
                    'pipe': 'true',
                    'executablePath': self.chrome_path,
                    'headless': True,
                    'args': [
                        '--headless',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ],
                },
            )

            page = await browser.newPage()
            file_url = f'file:///{temp_html_path}'
            await page.goto(file_url, {'waitUntil': 'networkidle2'})
            await page.pdf({'path': str(pdf_path), 'format': 'A4'})
            await browser.close()

            logger.info(f"PDF generated successfully: {pdf_path}")

        finally:
            # Clean up temporary HTML file
            if temp_html_path.exists():
                temp_html_path.unlink()
                logger.debug(f"Removed temporary HTML: {temp_html_path}")

    def generate_pdf(self, lease: Lease) -> Path:
        """
        Generate PDF contract for a lease.

        Args:
            lease: Lease instance

        Returns:
            Path to generated PDF file

        Raises:
            ContractGenerationError: If PDF generation fails
        """
        logger.info(f"Starting PDF generation for Lease #{lease.id}")

        try:
            # Prepare context and render HTML
            context = self.prepare_contract_context(lease)
            html_content = self.render_html(context)

            # Determine output paths
            building_dir = Path(settings.BASE_DIR) / self.output_dir / str(
                lease.apartment.building.street_number
            )
            building_dir.mkdir(parents=True, exist_ok=True)

            pdf_filename = f"contract_apto_{lease.apartment.number}_{lease.id}.pdf"
            pdf_path = building_dir / pdf_filename
            temp_html_path = building_dir / f"temp_contract_{lease.id}.html"

            # Generate PDF
            asyncio.run(self._generate_pdf_async(
                html_content,
                pdf_path,
                temp_html_path
            ))

            # Update lease status
            lease.contract_generated = True
            lease.save(update_fields=['contract_generated'])

            logger.info(f"Contract generated successfully for Lease #{lease.id}: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(
                f"Contract generation failed for Lease #{lease.id}: {str(e)}",
                exc_info=True
            )
            raise ContractGenerationError(
                f"Failed to generate contract: {str(e)}"
            ) from e

    def get_contract_path(self, lease: Lease) -> Optional[Path]:
        """
        Get path to existing contract PDF if it exists.

        Args:
            lease: Lease instance

        Returns:
            Path to PDF if exists, None otherwise
        """
        building_dir = Path(settings.BASE_DIR) / self.output_dir / str(
            lease.apartment.building.street_number
        )
        pdf_filename = f"contract_apto_{lease.apartment.number}_{lease.id}.pdf"
        pdf_path = building_dir / pdf_filename

        if pdf_path.exists():
            return pdf_path
        return None
```

### Week 3: Refactor Views to Use Services

#### Day 11-13: Update LeaseViewSet

**Task 2.5.1: Refactor LeaseViewSet** (8 hours)

**File: `core\views.py`** (complete rewrite)
```python
"""
API views for the core application.

This module now delegates business logic to service classes,
maintaining thin views focused on HTTP request/response handling.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from django.db.models import QuerySet
from typing import Optional
import logging

from .models import Building, Furniture, Apartment, Tenant, Lease
from .serializers import (
    BuildingSerializer, FurnitureSerializer, ApartmentSerializer,
    TenantSerializer, LeaseSerializer
)
from .services.contract_service import ContractService, ContractGenerationError
from .services.fee_calculator_service import FeeCalculatorService

logger = logging.getLogger(__name__)


class BuildingViewSet(viewsets.ModelViewSet):
    """ViewSet for Building CRUD operations"""
    queryset: QuerySet[Building] = Building.objects.all()
    serializer_class = BuildingSerializer


class FurnitureViewSet(viewsets.ModelViewSet):
    """ViewSet for Furniture CRUD operations"""
    queryset: QuerySet[Furniture] = Furniture.objects.all()
    serializer_class = FurnitureSerializer


class ApartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Apartment CRUD operations"""
    queryset: QuerySet[Apartment] = Apartment.objects.all()
    serializer_class = ApartmentSerializer


class TenantViewSet(viewsets.ModelViewSet):
    """ViewSet for Tenant CRUD operations"""
    queryset: QuerySet[Tenant] = Tenant.objects.all()
    serializer_class = TenantSerializer


class LeaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lease CRUD operations and special actions.

    Business logic is delegated to service classes:
    - ContractService for PDF generation
    - FeeCalculatorService for fee calculations
    """
    queryset: QuerySet[Lease] = Lease.objects.all()
    serializer_class = LeaseSerializer

    def __init__(self, *args, **kwargs):
        """Initialize viewset with service dependencies"""
        super().__init__(*args, **kwargs)
        self.contract_service = ContractService()

    @action(detail=True, methods=['post'])
    def generate_contract(
        self,
        request: Request,
        pk: Optional[int] = None
    ) -> Response:
        """
        Generate PDF contract for a lease.

        Endpoint: POST /api/leases/{id}/generate_contract/

        Returns:
            200: Contract generated successfully with pdf_path
            500: Contract generation failed
        """
        lease: Lease = self.get_object()
        logger.info(f"Contract generation requested for Lease #{lease.id}")

        try:
            pdf_path = self.contract_service.generate_pdf(lease)

            return Response(
                {
                    "message": "Contrato gerado com sucesso!",
                    "pdf_path": str(pdf_path)
                },
                status=status.HTTP_200_OK
            )

        except ContractGenerationError as e:
            logger.error(f"Contract generation failed: {str(e)}")
            return Response(
                {"error": "Erro ao gerar contrato. Verifique os logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def calculate_late_fee(
        self,
        request: Request,
        pk: Optional[int] = None
    ) -> Response:
        """
        Calculate late payment fee for a lease.

        Endpoint: GET /api/leases/{id}/calculate_late_fee/

        Returns:
            200: Fee calculation with late_days and late_fee
        """
        lease: Lease = self.get_object()
        logger.info(f"Late fee calculation requested for Lease #{lease.id}")

        result = FeeCalculatorService.calculate_late_fee(
            rental_value=lease.rental_value,
            due_day=lease.due_day
        )

        if result['is_late']:
            return Response(
                {
                    "late_days": result['late_days'],
                    "late_fee": str(result['late_fee'])
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"message": "Aluguel não está atrasado."},
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['post'])
    def change_due_date(
        self,
        request: Request,
        pk: Optional[int] = None
    ) -> Response:
        """
        Change lease due date with fee calculation.

        Endpoint: POST /api/leases/{id}/change_due_date/
        Body: {"new_due_day": <1-31>}

        Returns:
            200: Due date changed with fee amount
            400: Invalid input
        """
        lease: Lease = self.get_object()
        new_due_day = request.data.get('new_due_day')

        if not new_due_day:
            return Response(
                {"error": "Campo new_due_day é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_due_day = int(new_due_day)

            if not (1 <= new_due_day <= 31):
                return Response(
                    {"error": "new_due_day deve estar entre 1 e 31."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Calculate fee
            fee = FeeCalculatorService.calculate_due_date_change_fee(
                rental_value=lease.rental_value,
                current_due_day=lease.due_day,
                new_due_day=new_due_day
            )

            # Update lease
            old_due_day = lease.due_day
            lease.due_day = new_due_day
            lease.save(update_fields=['due_day'])

            logger.info(
                f"Lease #{lease.id} due date changed from {old_due_day} to {new_due_day}, "
                f"fee: {fee}"
            )

            return Response(
                {
                    "message": "Dia de vencimento alterado.",
                    "old_due_day": old_due_day,
                    "new_due_day": new_due_day,
                    "fee": str(fee)
                },
                status=status.HTTP_200_OK
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid due date value: {e}")
            return Response(
                {"error": "Valor inválido para new_due_day."},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**Task 2.5.2: Update Tests for Refactored Views** (6 hours)

**File: `tests\integration\test_api_views.py`** (update with service mocking)
```python
"""
Integration tests for refactored API views
"""
import pytest
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from pathlib import Path
from decimal import Decimal

from core.models import Lease
from core.services.contract_service import ContractGenerationError
from tests.fixtures.factories import LeaseFactory


@pytest.mark.django_db
class TestLeaseAPIWithServices:
    """Test Lease API endpoints with service mocking"""

    def test_generate_contract_success(self, api_client):
        """Test successful contract generation"""
        lease = LeaseFactory()

        with patch('core.views.ContractService.generate_pdf') as mock_generate:
            mock_generate.return_value = Path('/fake/path/contract.pdf')

            url = reverse('lease-generate-contract', args=[lease.id])
            response = api_client.post(url)

            assert response.status_code == status.HTTP_200_OK
            assert 'pdf_path' in response.data
            mock_generate.assert_called_once()

    def test_generate_contract_failure(self, api_client):
        """Test contract generation failure handling"""
        lease = LeaseFactory()

        with patch('core.views.ContractService.generate_pdf') as mock_generate:
            mock_generate.side_effect = ContractGenerationError("PDF generation failed")

            url = reverse('lease-generate-contract', args=[lease.id])
            response = api_client.post(url)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert 'error' in response.data

    def test_calculate_late_fee_with_service(self, api_client):
        """Test late fee calculation using service"""
        lease = LeaseFactory(due_day=5, rental_value=Decimal('1500.00'))

        with patch('core.views.FeeCalculatorService.calculate_late_fee') as mock_calc:
            mock_calc.return_value = {
                'late_days': 10,
                'late_fee': Decimal('25.00'),
                'is_late': True
            }

            url = reverse('lease-calculate-late-fee', args=[lease.id])
            response = api_client.get(url)

            assert response.status_code == status.HTTP_200_OK
            assert response.data['late_days'] == 10
            assert response.data['late_fee'] == '25.00'
```

#### Day 14-15: Integration Testing and Documentation

**Task 2.6.1: End-to-End Integration Tests** (6 hours)

**File: `tests\integration\test_lease_workflow.py`**
```python
"""
End-to-end integration tests for complete lease workflows
"""
import pytest
from rest_framework import status
from django.urls import reverse
from decimal import Decimal
from datetime import date

from core.models import Lease
from tests.fixtures.factories import (
    BuildingFactory, ApartmentFactory, TenantFactory, FurnitureFactory
)


@pytest.mark.django_db
class TestCompleteLeaseWorkflow:
    """Test complete lease creation and management workflow"""

    def test_create_lease_and_generate_contract(self, api_client, mocker):
        """Test full workflow: create lease -> generate contract"""
        # Setup
        building = BuildingFactory(street_number=836)
        furniture1 = FurnitureFactory(name="Fogão")
        furniture2 = FurnitureFactory(name="Geladeira")
        apartment = ApartmentFactory(
            building=building,
            number=102,
            furnitures=[furniture1, furniture2]
        )
        tenant = TenantFactory(furnitures=[furniture1])  # Has own stove

        # Step 1: Create lease
        lease_data = {
            'apartment_id': apartment.id,
            'responsible_tenant_id': tenant.id,
            'tenant_ids': [tenant.id],
            'start_date': '2025-01-15',
            'validity_months': 12,
            'due_day': 10,
            'rental_value': '1500.00',
            'cleaning_fee': '200.00',
            'tag_fee': '50.00'
        }

        url = reverse('lease-list')
        response = api_client.post(url, lease_data)

        assert response.status_code == status.HTTP_201_CREATED
        lease_id = response.data['id']

        # Step 2: Generate contract
        mock_pdf = mocker.patch('core.services.contract_service.asyncio.run')

        url = reverse('lease-generate-contract', args=[lease_id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'pdf_path' in response.data

        # Verify lease updated
        lease = Lease.objects.get(id=lease_id)
        assert lease.contract_generated is True

    def test_lease_due_date_change_workflow(self, api_client):
        """Test workflow: create lease -> change due date"""
        lease = LeaseFactory(
            due_day=10,
            rental_value=Decimal('1500.00')
        )

        # Change due date from 10 to 15
        url = reverse('lease-change-due-date', args=[lease.id])
        response = api_client.post(url, {'new_due_day': 15})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['old_due_day'] == 10
        assert response.data['new_due_day'] == 15
        assert 'fee' in response.data

        # Verify lease updated
        lease.refresh_from_db()
        assert lease.due_day == 15
```

**Task 2.6.2: Service Layer Documentation** (4 hours)

**File: `docs\architecture\service_layer.md`**
```markdown
# Service Layer Architecture

## Overview

The service layer encapsulates business logic, separating it from views and making it reusable and testable.

## Services

### FeeCalculatorService

**Location:** `core/services/fee_calculator_service.py`

**Responsibilities:**
- Calculate daily rental rates
- Calculate late payment fees
- Calculate due date change fees
- Calculate tag fees
- Calculate total initial costs

**Usage Example:**
```python
from core.services.fee_calculator_service import FeeCalculatorService

# Calculate late fee
result = FeeCalculatorService.calculate_late_fee(
    rental_value=Decimal('1500.00'),
    due_day=10
)
print(result)  # {'late_days': 5, 'late_fee': Decimal('12.50'), 'is_late': True}
```

### DateCalculatorService

**Location:** `core/services/date_calculator_service.py`

**Responsibilities:**
- Calculate next month dates
- Calculate lease end dates
- Handle leap year edge cases
- Check rent due status

**Usage Example:**
```python
from core.services.date_calculator_service import DateCalculatorService

dates = DateCalculatorService.calculate_lease_dates(
    start_date=date(2025, 1, 15),
    validity_months=12
)
print(dates['final_date'])  # 2026-01-15
```

### ContractService

**Location:** `core/services/contract_service.py`

**Responsibilities:**
- Generate PDF contracts
- Render contract templates
- Calculate contract furniture
- Manage contract files

**Usage Example:**
```python
from core.services.contract_service import ContractService

service = ContractService()
pdf_path = service.generate_pdf(lease)
print(f"Contract generated: {pdf_path}")
```

## Benefits

1. **Separation of Concerns**: Business logic separate from HTTP handling
2. **Reusability**: Services can be used from views, management commands, celery tasks
3. **Testability**: Services can be unit tested without HTTP layer
4. **Maintainability**: Changes to business logic isolated to service classes
5. **Dependency Injection**: Services can be mocked for testing

## Design Patterns

- **Service Pattern**: Encapsulate business logic in dedicated service classes
- **Dependency Injection**: Views receive service instances, can be mocked
- **Single Responsibility**: Each service has one clear purpose
- **Open/Closed**: Services can be extended without modifying existing code
```

### Deliverables

- [ ] Service layer directory structure created
- [ ] FeeCalculatorService implemented with 100% test coverage
- [ ] DateCalculatorService implemented with 100% test coverage
- [ ] ContractService implemented with 80%+ test coverage
- [ ] LeaseViewSet refactored to use services
- [ ] All API tests pass with service integration
- [ ] End-to-end integration tests created
- [ ] Service layer documentation complete

### Success Criteria

- ✅ Views reduced from 113 lines to <50 lines
- ✅ All business logic moved to services
- ✅ Service test coverage >90%
- ✅ All existing API tests pass
- ✅ Zero breaking changes to API

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking API changes | Low | High | Comprehensive integration tests |
| PDF generation issues | Medium | Medium | Mock in tests, test manually |
| Service complexity | Low | Medium | Keep services focused, single responsibility |
| Regression bugs | Medium | High | Full test coverage before refactoring |

### Rollback Strategy

- Keep old views.py as views_old.py backup
- Git branch allows easy revert
- API contract unchanged, frontend unaffected

---

## Phases 3-8 Summary

Due to length constraints, I'll provide summaries for the remaining phases:

### Phase 3: Domain Model Refinement (2 weeks)
- Remove data redundancy between Apartment and Lease
- Create value objects for Brazilian-specific data (CPF, CNPJ)
- Implement model validators
- Add database indexes for performance

### Phase 4: Infrastructure Improvements (2 weeks)
- **ChromaDB Integration**: Evaluate and implement semantic search for contracts/leases
- Abstract PDF generation (Strategy pattern for multiple engines)
- Implement repository pattern
- Add caching layer (Redis)
- Create management commands

### Phase 5: Database Normalization (2 weeks)
- Create Payment model for tracking rent payments
- Create Expense model for property expenses
- Add audit trail (django-simple-history)
- Data migration scripts
- Backward compatibility layer

### Phase 6: Security & Configuration (1 week)
- Implement authentication (JWT tokens)
- Add permission system
- Environment-based configuration
- Secrets management
- Security audit and fixes

### Phase 7: Advanced Features Foundation (2 weeks)
- Financial dashboard API endpoints
- Payment tracking system
- Document generation framework (multiple document types)
- ChromaDB-powered semantic search
- Notification system foundation

### Phase 8: Cleanup & Documentation (1 week)
- Remove deprecated code
- Final code quality improvements
- API documentation (OpenAPI/Swagger)
- Deployment guides
- Performance optimization

---

## Monitoring Progress

### Weekly Checklist

**Week Start:**
- [ ] Review previous week's deliverables
- [ ] Create database backup
- [ ] Pull latest from develop branch
- [ ] Review this week's tasks

**Week End:**
- [ ] Run full test suite
- [ ] Check code coverage
- [ ] Update metrics report
- [ ] Create pull request
- [ ] Tag weekly release

### Metrics to Track

| Metric | Baseline | Target | Current |
|--------|----------|--------|---------|
| Test Coverage | 0% | 80% | - |
| Lines of Code | 300 | 500 | - |
| Cyclomatic Complexity | 15 | 5 | - |
| Pylint Score | 5/10 | 8/10 | - |
| API Response Time | - | <200ms | - |
| Number of SOLID Violations | 12 | 0 | - |

---

## Risk Management

### High-Risk Areas

1. **Database Migrations (Phase 5)**
   - **Risk**: Data loss or corruption
   - **Mitigation**: Multiple backups, test on staging, reversible migrations

2. **PDF Generation Changes (Phase 4)**
   - **Risk**: Contracts fail to generate
   - **Mitigation**: Keep old implementation, feature flag, gradual rollout

3. **API Breaking Changes**
   - **Risk**: Frontend integration breaks
   - **Mitigation**: API versioning, backward compatibility layer

### Contingency Plans

- **Phase takes too long**: Reduce scope, move non-critical tasks to next phase
- **Critical bug discovered**: Pause refactoring, fix bug, add regression test
- **Team capacity reduced**: Prioritize critical phases (0, 1, 2, 6), defer others

---

## Success Metrics

### Phase 0-2 Complete (6 weeks)
- ✅ 60%+ test coverage
- ✅ CI/CD pipeline active
- ✅ Service layer extracted
- ✅ Views <50 lines each
- ✅ Type hints on all code
- ✅ Logging infrastructure active

### All Phases Complete (16 weeks)
- ✅ 80%+ test coverage
- ✅ Zero SOLID violations
- ✅ Database normalized
- ✅ ChromaDB integrated for semantic search
- ✅ Authentication implemented
- ✅ Payment tracking system operational
- ✅ API documentation complete
- ✅ Deployment automated

---

## Appendix

### Tools and Technologies

**Phase 0-1:**
- pytest, pytest-django, pytest-cov, factory-boy
- black, isort, flake8, mypy, pylint
- pre-commit, GitHub Actions
- python-decouple, docker-compose

**Phase 2:**
- Service layer pattern
- Dependency injection

**Phase 4:**
- **ChromaDB** (semantic search and document indexing)
- Redis (caching)
- Strategy pattern (PDF generation)

**Phase 5:**
- django-simple-history (audit trail)
- Django migrations

**Phase 6:**
- djangorestframework-simplejwt
- django-environ

**Phase 7:**
- Celery (async tasks)
- ChromaDB collections for advanced search

### References

- SOLID Principles: https://en.wikipedia.org/wiki/SOLID
- Domain-Driven Design: https://martinfowler.com/bliki/DomainDrivenDesign.html
- Django Best Practices: https://djangobestpractices.com/
- ChromaDB Documentation: https://docs.trychroma.com/

---

## Conclusion

This refactoring plan provides a structured, incremental approach to transforming the Condomínios Manager into a well-architected, maintainable system. The phased approach ensures:

1. **Safety**: Comprehensive testing before changes
2. **Stability**: No breaking changes to existing APIs
3. **Progress**: Weekly deliverables and visible improvements
4. **Quality**: Industry best practices and SOLID principles
5. **Future-Ready**: Foundation for advanced features

The plan prioritizes critical phases (Foundation, Services, Security) while allowing flexibility for lower-priority improvements. **ChromaDB integration** in Phase 4 provides powerful semantic search capabilities without external dependencies.

By following this plan, the team will achieve a modern, scalable Django application ready for future growth.
