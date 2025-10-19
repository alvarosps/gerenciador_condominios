# Migration Guide: From Monolithic to Layered Architecture
## Step-by-Step Implementation Plan

This guide provides a practical, incremental migration path from the current monolithic structure to the recommended layered architecture. Each step can be completed and tested independently without breaking existing functionality.

---

## Prerequisites

**Install New Dependencies**
```bash
pip install python-decouple dependency-injector pytest pytest-django factory-boy
```

**Update requirements.txt**
```txt
# Add to requirements.txt
python-decouple==3.8
dependency-injector==4.41.0
pytest==7.4.3
pytest-django==4.5.2
factory-boy==3.3.0
```

---

## Week 1: Foundation & Configuration

### Day 1: Environment Configuration

**1. Create `.env` file (DO NOT commit)**
```bash
# .env
DJANGO_ENV=development
SECRET_KEY=django-insecure-b7ya%t^1&z1v#af1mlzjsm*$l9o^zj!h9a3*)tf@2k&z8b*^)h
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=condominio
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

PDF_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
PDF_TIMEOUT=30000

STORAGE_TYPE=filesystem
STORAGE_BASE_PATH=./contracts

FEE_LATE_RATE=0.05
FEE_TAG_SINGLE=50.00
FEE_TAG_MULTIPLE=80.00
FEE_DAYS_PER_MONTH=30

LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log
```

**2. Create `.env.example` (for version control)**
```bash
cp .env .env.example
# Edit .env.example to remove sensitive values
```

**3. Add to `.gitignore`**
```
# .gitignore
.env
*.pyc
__pycache__/
db.sqlite3
logs/
contracts/
```

**4. Create environment-based settings**
```bash
mkdir -p config/settings
```

**File: `config/settings/base.py`**
```python
# Move all content from condominios_manager/settings.py
# Replace hardcoded values with:

from decouple import config, Csv

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Add new configuration sections
PDF_GENERATION = {
    'CHROME_PATH': config('PDF_CHROME_PATH', default=None),
    'TIMEOUT': config('PDF_TIMEOUT', default=30000, cast=int),
}

FEE_CONFIGURATION = {
    'LATE_RATE': config('FEE_LATE_RATE', default=0.05, cast=float),
    'TAG_SINGLE': config('FEE_TAG_SINGLE', default=50.00, cast=float),
    'TAG_MULTIPLE': config('FEE_TAG_MULTIPLE', default=80.00, cast=float),
    'DAYS_PER_MONTH': config('FEE_DAYS_PER_MONTH', default=30, cast=int),
}
```

**File: `config/settings/development.py`**
```python
from .base import *

DEBUG = True
```

**File: `config/settings/production.py`**
```python
from .base import *

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**5. Update manage.py**
```python
#!/usr/bin/env python
import os
import sys
from decouple import config

if __name__ == '__main__':
    env = config('DJANGO_ENV', default='development')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'config.settings.{env}')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django.") from exc
    execute_from_command_line(sys.argv)
```

**6. Test**
```bash
python manage.py check
python manage.py runserver
```

### Day 2: Create New App Structure

**1. Create apps directory**
```bash
mkdir apps
touch apps/__init__.py
```

**2. Create shared app (foundation)**
```bash
python manage.py startapp shared apps/shared
```

**3. Create shared infrastructure**
```bash
mkdir -p apps/shared/{domain,infrastructure,api}
```

**File: `apps/shared/infrastructure/config.py`**
```python
from django.conf import settings

class AppConfig:
    """Centralized configuration access."""

    @staticmethod
    def get_pdf_chrome_path() -> str:
        return settings.PDF_GENERATION.get('CHROME_PATH')

    @staticmethod
    def get_pdf_timeout() -> int:
        return settings.PDF_GENERATION.get('TIMEOUT', 30000)

    @staticmethod
    def get_late_fee_rate() -> float:
        return settings.FEE_CONFIGURATION.get('LATE_RATE', 0.05)

    @staticmethod
    def get_tag_fee_single() -> float:
        return settings.FEE_CONFIGURATION.get('TAG_SINGLE', 50.00)

    @staticmethod
    def get_tag_fee_multiple() -> float:
        return settings.FEE_CONFIGURATION.get('TAG_MULTIPLE', 80.00)

    @staticmethod
    def get_fee_days_per_month() -> int:
        return settings.FEE_CONFIGURATION.get('DAYS_PER_MONTH', 30)
```

**File: `apps/shared/infrastructure/formatters.py`**
```python
# Move from core/utils.py
from num2words import num2words

def number_to_words(value):
    try:
        return num2words(float(value), lang='pt_BR')
    except Exception as e:
        print(f"Erro ao converter número para extenso: {e}")
        return value

def format_currency(value):
    return f"R${value:,.2f}"
```

**File: `apps/shared/domain/exceptions.py`**
```python
class DomainException(Exception):
    """Base exception for domain layer."""
    pass

class NotFoundError(DomainException):
    """Entity not found."""
    pass

class ValidationError(DomainException):
    """Validation failed."""
    pass
```

**4. Update settings to include apps**
```python
# config/settings/base.py
INSTALLED_APPS = [
    # ... django apps
    'apps.shared',
]
```

**5. Test**
```bash
python manage.py check
```

### Day 3-4: Create Bounded Context Apps

**1. Create leases app**
```bash
python manage.py startapp leases apps/leases
mkdir -p apps/leases/{domain,application,infrastructure,api}
```

**2. Create properties app**
```bash
python manage.py startapp properties apps/properties
mkdir -p apps/properties/{domain,application,infrastructure,api}
```

**3. Create tenants app**
```bash
python manage.py startapp tenants apps/tenants
mkdir -p apps/tenants/{domain,application,infrastructure,api}
```

**4. Create documents app**
```bash
python manage.py startapp documents apps/documents
mkdir -p apps/documents/{domain,application,infrastructure}
mkdir -p apps/documents/infrastructure/pdf_generators
```

**5. Update INSTALLED_APPS**
```python
# config/settings/base.py
INSTALLED_APPS = [
    # Django apps...
    'corsheaders',
    'rest_framework',
    # Local apps
    'apps.properties',
    'apps.leases',
    'apps.tenants',
    'apps.documents',
    'apps.shared',
    'core',  # Keep old app during migration
]
```

### Day 5: Set Up Testing Infrastructure

**1. Create pytest configuration**

**File: `pytest.ini`**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
testpaths = tests
```

**File: `config/settings/test.py`**
```python
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
```

**2. Create test directories**
```bash
mkdir -p tests/{unit,integration,domain,application}
touch tests/__init__.py
```

**3. Create test fixtures**

**File: `tests/fixtures.py`**
```python
import pytest
from decimal import Decimal
from datetime import date

@pytest.fixture
def sample_lease_data():
    return {
        'start_date': date(2025, 1, 15),
        'validity_months': 12,
        'due_day': 10,
        'rental_value': Decimal('1500.00'),
        'cleaning_fee': Decimal('200.00'),
        'tag_fee': Decimal('50.00'),
    }
```

**4. Test setup**
```bash
pytest
```

---

## Week 2: Domain Layer Migration

### Day 1: Extract Domain Services

**File: `apps/leases/domain/services.py`**
```python
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from apps.shared.infrastructure.config import AppConfig


class DateCalculationService:
    """Domain service for date calculations."""

    @staticmethod
    def calculate_final_date(start_date: date, validity_months: int) -> date:
        """Calculate lease final date with leap year handling."""
        calculated_final_date = start_date + relativedelta(months=validity_months)

        # Special case: Feb 29 -> Feb 28 -> March 1
        if start_date.month == 2 and start_date.day == 29:
            if calculated_final_date.month == 2 and calculated_final_date.day == 28:
                calculated_final_date = calculated_final_date + timedelta(days=1)

        return calculated_final_date

    @staticmethod
    def calculate_next_month_date(start_date: date) -> date:
        """Calculate next month date."""
        return start_date + relativedelta(months=1)

    @staticmethod
    def days_late(due_day: int, current_date: date) -> int:
        """Calculate days late."""
        if current_date.day <= due_day:
            return 0
        return current_date.day - due_day


class FeeCalculationEngine:
    """Domain service for fee calculations."""

    @classmethod
    def calculate_late_fee(cls, rental_value: Decimal, days_late: int) -> Decimal:
        """Calculate late fee."""
        if days_late <= 0:
            return Decimal('0.00')

        late_rate = Decimal(str(AppConfig.get_late_fee_rate()))
        days_per_month = Decimal(str(AppConfig.get_fee_days_per_month()))

        daily_rate = rental_value / days_per_month
        late_fee = daily_rate * Decimal(days_late) * late_rate

        return late_fee.quantize(Decimal('0.01'))

    @classmethod
    def calculate_due_date_change_fee(
        cls,
        rental_value: Decimal,
        current_due_day: int,
        new_due_day: int
    ) -> Decimal:
        """Calculate fee for changing due date."""
        days_difference = abs(new_due_day - current_due_day)
        days_per_month = Decimal(str(AppConfig.get_fee_days_per_month()))

        daily_rate = rental_value / days_per_month
        fee = daily_rate * Decimal(days_difference)

        return fee.quantize(Decimal('0.01'))

    @classmethod
    def calculate_tag_fee(cls, number_of_tenants: int) -> Decimal:
        """Calculate tag fee based on number of tenants."""
        if number_of_tenants == 1:
            return Decimal(str(AppConfig.get_tag_fee_single()))
        return Decimal(str(AppConfig.get_tag_fee_multiple()))
```

### Day 2: Write Domain Tests

**File: `tests/domain/test_date_calculation_service.py`**
```python
import pytest
from datetime import date
from apps.leases.domain.services import DateCalculationService


def test_calculate_final_date_normal():
    """Test normal final date calculation."""
    start = date(2025, 1, 15)
    final = DateCalculationService.calculate_final_date(start, 12)
    assert final == date(2026, 1, 15)


def test_calculate_final_date_leap_year():
    """Test leap year edge case."""
    start = date(2024, 2, 29)
    final = DateCalculationService.calculate_final_date(start, 12)
    assert final == date(2025, 3, 1)  # Feb 28 -> March 1


def test_days_late_on_time():
    """Test days late when payment is on time."""
    days = DateCalculationService.days_late(10, date(2025, 1, 10))
    assert days == 0


def test_days_late_overdue():
    """Test days late when payment is overdue."""
    days = DateCalculationService.days_late(10, date(2025, 1, 15))
    assert days == 5
```

**File: `tests/domain/test_fee_calculation_engine.py`**
```python
import pytest
from decimal import Decimal
from apps.leases.domain.services import FeeCalculationEngine


def test_calculate_late_fee():
    """Test late fee calculation."""
    rental = Decimal('1500.00')
    days = 5
    fee = FeeCalculationEngine.calculate_late_fee(rental, days)
    # (1500 / 30) * 5 * 0.05 = 12.50
    assert fee == Decimal('12.50')


def test_calculate_late_fee_zero_days():
    """Test late fee with zero days."""
    rental = Decimal('1500.00')
    fee = FeeCalculationEngine.calculate_late_fee(rental, 0)
    assert fee == Decimal('0.00')


def test_calculate_tag_fee_single():
    """Test tag fee for single tenant."""
    fee = FeeCalculationEngine.calculate_tag_fee(1)
    assert fee == Decimal('50.00')


def test_calculate_tag_fee_multiple():
    """Test tag fee for multiple tenants."""
    fee = FeeCalculationEngine.calculate_tag_fee(2)
    assert fee == Decimal('80.00')
```

**Run tests**
```bash
pytest tests/domain/
```

### Day 3-5: Update Existing Views to Use Domain Services

**Update `core/views.py` to use new domain services**
```python
# core/views.py
from apps.leases.domain.services import DateCalculationService, FeeCalculationEngine

class LeaseViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @action(detail=True, methods=['post'])
    def generate_contract(self, request, pk=None):
        lease = self.get_object()

        try:
            # BEFORE: Inline date calculation
            # next_month_date = (start_date + relativedelta(months=1)).strftime("%d/%m/%Y")

            # AFTER: Use domain service
            start_date = lease.start_date
            next_month_date = DateCalculationService.calculate_next_month_date(
                start_date
            ).strftime("%d/%m/%Y")

            final_date = DateCalculationService.calculate_final_date(
                start_date,
                lease.validity_months
            ).strftime("%d/%m/%Y")

            # BEFORE: Inline tag fee calculation
            # valor_tags = 50 if len(lease.tenants.all()) == 1 else 80

            # AFTER: Use domain service
            valor_tags = FeeCalculationEngine.calculate_tag_fee(
                len(lease.tenants.all())
            )

            # ... rest of the code

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def calculate_late_fee(self, request, pk=None):
        lease = self.get_object()
        today = date.today()

        # BEFORE: Inline calculation
        # if today.day > due_day:
        #     atraso_dias = today.day - due_day
        #     daily_rate = lease.rental_value / 30
        #     multa = daily_rate * atraso_dias * 0.05

        # AFTER: Use domain service
        days_late = DateCalculationService.days_late(lease.due_day, today)
        if days_late > 0:
            multa = FeeCalculationEngine.calculate_late_fee(
                lease.rental_value,
                days_late
            )
            return Response({
                "late_days": days_late,
                "late_fee": str(multa)
            }, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Aluguel não está atrasado."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def change_due_date(self, request, pk=None):
        lease = self.get_object()
        new_due_day = request.data.get('new_due_day')

        if not new_due_day:
            return Response({"error": "Campo new_due_day é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_due_day = int(new_due_day)

            # BEFORE: Inline calculation
            # diff_days = abs(new_due_day - current_due_day)
            # daily_rate = lease.rental_value / 30
            # fee = daily_rate * diff_days

            # AFTER: Use domain service
            fee = FeeCalculationEngine.calculate_due_date_change_fee(
                lease.rental_value,
                lease.due_day,
                new_due_day
            )

            lease.due_day = new_due_day
            lease.save()

            return Response({
                "message": "Dia de vencimento alterado.",
                "fee": str(fee)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**Test integration**
```bash
python manage.py runserver
# Test endpoints manually or with Postman
```

---

## Week 3: Application Layer & Repository Pattern

### Day 1-2: Create Repository Interfaces

**File: `apps/leases/domain/repositories.py`**
```python
from abc import ABC, abstractmethod
from typing import Optional, List

class ILeaseRepository(ABC):
    """Repository interface for Lease."""

    @abstractmethod
    def get_by_id(self, lease_id: int) -> Optional['Lease']:
        pass

    @abstractmethod
    def save(self, lease: 'Lease') -> 'Lease':
        pass

    @abstractmethod
    def delete(self, lease_id: int) -> bool:
        pass
```

**File: `apps/leases/infrastructure/repositories.py`**
```python
from typing import Optional
from apps.leases.domain.repositories import ILeaseRepository
from core.models import Lease as LeaseModel


class DjangoLeaseRepository(ILeaseRepository):
    """Django ORM implementation of lease repository."""

    def get_by_id(self, lease_id: int) -> Optional[LeaseModel]:
        """Get lease by ID with related data."""
        try:
            return LeaseModel.objects.select_related(
                'apartment__building',
                'responsible_tenant'
            ).prefetch_related(
                'tenants',
                'apartment__furnitures',
                'responsible_tenant__furnitures'
            ).get(id=lease_id)
        except LeaseModel.DoesNotExist:
            return None

    def save(self, lease: LeaseModel) -> LeaseModel:
        """Save lease."""
        lease.save()
        return lease

    def delete(self, lease_id: int) -> bool:
        """Delete lease."""
        try:
            LeaseModel.objects.filter(id=lease_id).delete()
            return True
        except Exception:
            return False
```

### Day 3-4: Create Application Service

**File: `apps/leases/domain/exceptions.py`**
```python
from apps.shared.domain.exceptions import DomainException

class LeaseNotFoundError(DomainException):
    """Lease not found."""
    pass

class ContractGenerationError(DomainException):
    """Contract generation failed."""
    pass
```

**File: `apps/leases/application/services.py`**
```python
from apps.leases.domain.repositories import ILeaseRepository
from apps.leases.domain.exceptions import LeaseNotFoundError


class LeaseService:
    """Application service for lease operations."""

    def __init__(self, lease_repository: ILeaseRepository):
        self._lease_repo = lease_repository

    def get_lease(self, lease_id: int):
        """Get lease by ID."""
        lease = self._lease_repo.get_by_id(lease_id)
        if not lease:
            raise LeaseNotFoundError(f"Lease {lease_id} not found")
        return lease

    def calculate_late_fee_for_lease(self, lease_id: int):
        """Calculate late fee for a lease."""
        from datetime import date
        from apps.leases.domain.services import DateCalculationService, FeeCalculationEngine

        lease = self.get_lease(lease_id)
        today = date.today()

        days_late = DateCalculationService.days_late(lease.due_day, today)
        if days_late > 0:
            late_fee = FeeCalculationEngine.calculate_late_fee(
                lease.rental_value,
                days_late
            )
            return {
                'days_late': days_late,
                'late_fee': late_fee,
                'is_late': True
            }

        return {'is_late': False, 'late_fee': 0, 'days_late': 0}

    def change_lease_due_date(self, lease_id: int, new_due_day: int):
        """Change due date and calculate fee."""
        from apps.leases.domain.services import FeeCalculationEngine

        lease = self.get_lease(lease_id)

        if not 1 <= new_due_day <= 31:
            raise ValueError("Due day must be between 1 and 31")

        fee = FeeCalculationEngine.calculate_due_date_change_fee(
            lease.rental_value,
            lease.due_day,
            new_due_day
        )

        lease.due_day = new_due_day
        self._lease_repo.save(lease)

        return fee
```

### Day 5: Set Up Dependency Injection

**File: `apps/shared/infrastructure/container.py`**
```python
from dependency_injector import containers, providers
from apps.leases.application.services import LeaseService
from apps.leases.infrastructure.repositories import DjangoLeaseRepository


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""

    config = providers.Configuration()

    # Repositories
    lease_repository = providers.Singleton(DjangoLeaseRepository)

    # Application services
    lease_service = providers.Singleton(
        LeaseService,
        lease_repository=lease_repository
    )
```

**File: `config/__init__.py`**
```python
from apps.shared.infrastructure.container import Container

container = Container()
```

---

## Week 4: Refactor ViewSets to Use Services

### Update ViewSet

**File: `core/views.py`**
```python
from apps.shared.infrastructure.container import Container
from apps.leases.domain.exceptions import LeaseNotFoundError

class LeaseViewSet(viewsets.ModelViewSet):
    queryset = Lease.objects.all()
    serializer_class = LeaseSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lease_service = Container.lease_service()

    @action(detail=True, methods=['get'])
    def calculate_late_fee(self, request, pk=None):
        """Calculate late fee using service."""
        try:
            result = self._lease_service.calculate_late_fee_for_lease(int(pk))

            if result['is_late']:
                return Response({
                    "late_days": result['days_late'],
                    "late_fee": str(result['late_fee'])
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Aluguel não está atrasado."
                }, status=status.HTTP_200_OK)

        except LeaseNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def change_due_date(self, request, pk=None):
        """Change due date using service."""
        new_due_day = request.data.get('new_due_day')

        if not new_due_day:
            return Response(
                {"error": "Campo new_due_day é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fee = self._lease_service.change_lease_due_date(
                int(pk),
                int(new_due_day)
            )

            return Response({
                "message": "Dia de vencimento alterado.",
                "fee": str(fee)
            }, status=status.HTTP_200_OK)

        except LeaseNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

---

## Testing the Migration

### Integration Tests

**File: `tests/integration/test_lease_api.py`**
```python
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from decimal import Decimal

@pytest.mark.django_db
def test_calculate_late_fee_not_late(sample_lease):
    """Test late fee calculation when not late."""
    client = APIClient()
    url = reverse('lease-calculate-late-fee', kwargs={'pk': sample_lease.id})

    response = client.get(url)

    assert response.status_code == 200
    assert 'message' in response.data
    assert response.data['message'] == "Aluguel não está atrasado."


@pytest.mark.django_db
def test_change_due_date(sample_lease):
    """Test changing due date."""
    client = APIClient()
    url = reverse('lease-change-due-date', kwargs={'pk': sample_lease.id})

    response = client.post(url, {'new_due_day': 15})

    assert response.status_code == 200
    assert 'fee' in response.data
    assert 'message' in response.data
```

---

## Rollback Plan

If issues arise during migration:

**1. Keep old code alongside new code**
```python
# Keep both implementations temporarily
class LeaseViewSet(viewsets.ModelViewSet):
    USE_NEW_IMPLEMENTATION = False  # Feature flag

    def calculate_late_fee_old(self, request, pk=None):
        # Old implementation
        pass

    def calculate_late_fee_new(self, request, pk=None):
        # New implementation using service
        pass

    @action(detail=True, methods=['get'])
    def calculate_late_fee(self, request, pk=None):
        if self.USE_NEW_IMPLEMENTATION:
            return self.calculate_late_fee_new(request, pk)
        return self.calculate_late_fee_old(request, pk)
```

**2. Use environment variable to toggle**
```python
# .env
USE_NEW_ARCHITECTURE=False

# views.py
from decouple import config

USE_NEW_IMPLEMENTATION = config('USE_NEW_ARCHITECTURE', default=False, cast=bool)
```

**3. Gradual rollout**
- Week 1-2: New code alongside old (feature flagged off)
- Week 3: Enable for development environment
- Week 4: Enable for production after testing

---

## Success Criteria

**Week 1 Complete:**
- [ ] Environment configuration working
- [ ] All hardcoded values externalized
- [ ] New app structure created
- [ ] Tests run successfully

**Week 2 Complete:**
- [ ] Domain services extracted
- [ ] Unit tests for domain logic passing
- [ ] Old views using new domain services
- [ ] No breaking changes to API

**Week 3 Complete:**
- [ ] Repository pattern implemented
- [ ] Application services created
- [ ] Dependency injection working

**Week 4 Complete:**
- [ ] ViewSets refactored to use services
- [ ] Integration tests passing
- [ ] Code coverage > 70%
- [ ] Performance unchanged or improved

---

## Next Steps After Migration

1. **Add remaining features to service layer**
   - Contract generation
   - Document management

2. **Improve PDF generation**
   - Add WeasyPrint as alternative
   - Make generator pluggable

3. **Add background jobs**
   - Async contract generation
   - Scheduled expiration notifications

4. **Add caching**
   - Redis for lease summaries
   - Cache invalidation strategy

5. **Add authentication**
   - JWT tokens
   - Role-based access control

---

**Version:** 1.0
**Last Updated:** 2025-10-19
**Author:** Claude (Backend Architecture Specialist)
