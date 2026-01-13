# Database Refactoring Implementation Guide

## Executive Summary

This guide provides step-by-step instructions for implementing the database refactoring for the Condomínios Manager system. The refactoring addresses critical design issues including data redundancy, missing payment tracking, and lack of audit trails.

## Pre-Implementation Checklist

### 1. Backup Current Database
```bash
# Create full backup
pg_dump -U postgres -h localhost -d condominio -F custom -f backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup
pg_restore -l backup_20250119_120000.dump
```

### 2. Test Environment Setup
```bash
# Create test database
createdb -U postgres condominio_test

# Restore current data to test DB
pg_restore -U postgres -d condominio_test backup_20250119_120000.dump

# Update Django settings for test
# In settings.py, temporarily change database name to 'condominio_test'
```

### 3. Review Current Data
```sql
-- Check for data anomalies
SELECT
    a.id,
    a.rental_value as apt_rental,
    l.rental_value as lease_rental,
    a.contract_generated as apt_contract,
    l.contract_generated as lease_contract
FROM apartments a
LEFT JOIN leases l ON l.apartment_id = a.id
WHERE a.rental_value != l.rental_value
   OR a.contract_generated != l.contract_generated;

-- Check tenant payment configurations
SELECT
    t.id,
    t.name,
    t.rent_due_day as tenant_due,
    l.due_day as lease_due
FROM tenants t
JOIN leases l ON l.responsible_tenant_id = t.id
WHERE t.rent_due_day != l.due_day;
```

## Implementation Steps

### Phase 1: Database Schema Updates (Week 1)

#### Step 1.1: Run SQL Migration Scripts
```bash
# Connect to database
psql -U postgres -d condominio_test

# Run migration script
\i database_migration_scripts.sql

# Verify new tables
\dt *pricing*
\dt *payment*
\dt *document*
\dt *expense*
\dt *audit*
```

#### Step 1.2: Run Django Migrations
```bash
# Create migration files
python manage.py makemigrations

# Review migration SQL
python manage.py sqlmigrate core 0003_refactor_database

# Apply migrations
python manage.py migrate

# Verify migration status
python manage.py showmigrations
```

### Phase 2: Update Django Models (Week 2)

#### Step 2.1: Create New Models
Create file: `core/models_v2.py`

```python
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

class ApartmentPricing(models.Model):
    """Historical pricing for apartments"""
    apartment = models.ForeignKey(
        'Apartment',
        on_delete=models.CASCADE,
        related_name='pricing_history'
    )
    rental_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    cleaning_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-effective_date']
        constraints = [
            models.UniqueConstraint(
                fields=['apartment', 'is_current'],
                condition=models.Q(is_current=True),
                name='unique_current_price'
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_current:
            # Deactivate other current prices
            ApartmentPricing.objects.filter(
                apartment=self.apartment,
                is_current=True
            ).exclude(id=self.id).update(is_current=False)
        super().save(*args, **kwargs)

class Payment(models.Model):
    """Payment tracking for leases"""
    CATEGORY_CHOICES = [
        ('rent', 'Rent'),
        ('cleaning', 'Cleaning Fee'),
        ('deposit', 'Security Deposit'),
        ('late_fee', 'Late Fee'),
        ('damage', 'Damage'),
        ('other', 'Other')
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded')
    ]

    lease = models.ForeignKey(
        'Lease',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    due_date = models.DateField()
    paid_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    class Meta:
        ordering = ['-due_date', '-created_at']

    def save(self, *args, **kwargs):
        # Auto-update status
        if self.amount_paid >= self.amount_due:
            self.status = 'paid'
            if not self.paid_date:
                self.paid_date = timezone.now().date()
        elif self.amount_paid > 0:
            self.status = 'partial'
        elif self.due_date < timezone.now().date() and self.status == 'pending':
            self.status = 'overdue'
        super().save(*args, **kwargs)

    def calculate_late_fee(self):
        """Calculate late fee based on days overdue"""
        if self.status != 'overdue':
            return Decimal('0.00')

        days_late = (timezone.now().date() - self.due_date).days
        daily_rate = self.amount_due / 30
        return daily_rate * days_late * Decimal('0.05')  # 5% per day
```

#### Step 2.2: Update Existing Models
```python
# In core/models.py

class Apartment(models.Model):
    # Remove duplicate fields
    # DELETE: rental_value, cleaning_fee, is_rented, lease_date
    # DELETE: contract_generated, contract_signed, interfone_configured

    # Keep only apartment-specific fields
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    max_tenants = models.PositiveIntegerField()
    furnitures = models.ManyToManyField(Furniture, through='ApartmentFurniture')

    @property
    def current_price(self):
        """Get current pricing"""
        return self.pricing_history.filter(is_current=True).first()

    @property
    def is_rented(self):
        """Check if apartment has active lease"""
        return self.leases.filter(status='active').exists()

class Lease(models.Model):
    # Add status field
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('ending_soon', 'Ending Soon'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated')
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Add end_date calculation
    @property
    def end_date(self):
        from dateutil.relativedelta import relativedelta
        return self.start_date + relativedelta(months=self.validity_months)

    def get_pending_payments(self):
        """Get all pending payments"""
        return self.payments.filter(status__in=['pending', 'overdue'])

    def get_total_debt(self):
        """Calculate total outstanding debt"""
        pending = self.get_pending_payments()
        return sum(p.amount_due - p.amount_paid for p in pending)
```

### Phase 3: Update API Views and Serializers (Week 3)

#### Step 3.1: Create New Serializers
```python
# core/serializers_v2.py

from rest_framework import serializers
from .models import Payment, ApartmentPricing, Document

class PaymentSerializer(serializers.ModelSerializer):
    late_fee = serializers.SerializerMethodField()
    total_due = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'late_fee', 'total_due']

    def get_late_fee(self, obj):
        return obj.calculate_late_fee()

    def get_total_due(self, obj):
        return obj.amount_due + obj.calculate_late_fee() - obj.discount_amount

class ApartmentPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentPricing
        fields = '__all__'

    def validate(self, data):
        # Ensure no overlapping dates
        if data.get('is_current') and data.get('end_date'):
            raise serializers.ValidationError(
                "Current pricing cannot have an end date"
            )
        return data

class PaymentDashboardSerializer(serializers.Serializer):
    """Dashboard view of payments"""
    total_pending = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_overdue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_collected_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    overdue_count = serializers.IntegerField()
    upcoming_payments = PaymentSerializer(many=True)
```

#### Step 3.2: Create New API Views
```python
# core/views_v2.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q
from datetime import date, timedelta

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Payment dashboard summary"""
        today = date.today()
        month_start = today.replace(day=1)

        # Calculate totals
        pending = Payment.objects.filter(status='pending').aggregate(
            total=Sum('amount_due')
        )['total'] or 0

        overdue = Payment.objects.filter(status='overdue').aggregate(
            total=Sum('amount_due')
        )['total'] or 0

        collected = Payment.objects.filter(
            paid_date__gte=month_start,
            status='paid'
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        # Get upcoming payments
        upcoming = Payment.objects.filter(
            status='pending',
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7)
        )

        data = {
            'total_pending': pending,
            'total_overdue': overdue,
            'total_collected_month': collected,
            'overdue_count': Payment.objects.filter(status='overdue').count(),
            'upcoming_payments': PaymentSerializer(upcoming, many=True).data
        }

        return Response(data)

    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """Record a payment"""
        payment = self.get_object()
        amount = request.data.get('amount')
        method = request.data.get('payment_method')
        reference = request.data.get('reference')

        if not amount:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.amount_paid += Decimal(amount)
        payment.payment_method = method
        payment.transaction_reference = reference
        payment.save()  # Status will auto-update

        # Create audit log
        AuditLog.objects.create(
            table_name='payments',
            record_id=payment.id,
            action='UPDATE',
            change_summary=f'Payment of {amount} recorded',
            user_name=request.user.username if request.user.is_authenticated else 'anonymous'
        )

        return Response(PaymentSerializer(payment).data)

class LeaseViewSetV2(viewsets.ModelViewSet):
    """Enhanced Lease ViewSet with payment integration"""

    @action(detail=True, methods=['post'])
    def generate_monthly_payments(self, request, pk=None):
        """Generate monthly payments for a lease"""
        lease = self.get_object()
        month = request.data.get('month', date.today().replace(day=1))

        # Check if payment already exists
        existing = Payment.objects.filter(
            lease=lease,
            reference_month=month,
            payment_category='rent'
        ).first()

        if existing:
            return Response(
                {'message': 'Payment already exists', 'payment': PaymentSerializer(existing).data}
            )

        # Create new payment
        payment = Payment.objects.create(
            lease=lease,
            payment_category='rent',
            amount_due=lease.rental_value,
            due_date=month.replace(day=lease.due_day),
            reference_month=month
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
```

### Phase 4: Testing and Validation (Week 4)

#### Step 4.1: Create Test Suite
```python
# core/tests/test_database_refactoring.py

from django.test import TestCase
from django.db import IntegrityError
from core.models import Apartment, ApartmentPricing, Payment, Lease
from decimal import Decimal
from datetime import date

class ApartmentPricingTestCase(TestCase):
    def setUp(self):
        self.building = Building.objects.create(
            street_number=123,
            name="Test Building"
        )
        self.apartment = Apartment.objects.create(
            building=self.building,
            number=101,
            max_tenants=2
        )

    def test_only_one_current_price(self):
        """Ensure only one current price per apartment"""
        price1 = ApartmentPricing.objects.create(
            apartment=self.apartment,
            rental_value=Decimal('1000.00'),
            effective_date=date(2025, 1, 1),
            is_current=True
        )

        price2 = ApartmentPricing.objects.create(
            apartment=self.apartment,
            rental_value=Decimal('1100.00'),
            effective_date=date(2025, 2, 1),
            is_current=True
        )

        # Refresh price1 from DB
        price1.refresh_from_db()
        self.assertFalse(price1.is_current)
        self.assertTrue(price2.is_current)

class PaymentTestCase(TestCase):
    def test_auto_status_update(self):
        """Test automatic status updates"""
        payment = Payment.objects.create(
            lease=self.lease,
            payment_category='rent',
            amount_due=Decimal('1000.00'),
            due_date=date.today()
        )

        # Test partial payment
        payment.amount_paid = Decimal('500.00')
        payment.save()
        self.assertEqual(payment.status, 'partial')

        # Test full payment
        payment.amount_paid = Decimal('1000.00')
        payment.save()
        self.assertEqual(payment.status, 'paid')
        self.assertIsNotNone(payment.paid_date)

    def test_late_fee_calculation(self):
        """Test late fee calculation"""
        payment = Payment.objects.create(
            lease=self.lease,
            payment_category='rent',
            amount_due=Decimal('1000.00'),
            due_date=date.today() - timedelta(days=5),
            status='overdue'
        )

        # 5 days late * (1000/30) * 0.05 = 8.33
        expected_fee = Decimal('8.33')
        self.assertAlmostEqual(
            payment.calculate_late_fee(),
            expected_fee,
            places=2
        )
```

#### Step 4.2: Run Tests
```bash
# Run all tests
python manage.py test

# Run specific test class
python manage.py test core.tests.test_database_refactoring.PaymentTestCase

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Phase 5: Data Validation (Week 5)

#### Step 5.1: Validate Migration Results
```sql
-- Check pricing migration
SELECT
    a.id,
    a.number,
    ap.rental_value,
    ap.cleaning_fee,
    ap.is_current
FROM apartments a
LEFT JOIN apartment_pricing ap ON a.id = ap.apartment_id
WHERE ap.is_current = TRUE;

-- Check payment generation
SELECT
    l.id,
    COUNT(p.id) as payment_count,
    SUM(CASE WHEN p.status = 'pending' THEN 1 ELSE 0 END) as pending_count,
    SUM(p.amount_due) as total_due
FROM leases l
LEFT JOIN payments p ON l.id = p.lease_id
GROUP BY l.id;

-- Check for orphaned records
SELECT * FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM lease_tenants lt WHERE lt.tenant_id = t.id
);
```

#### Step 5.2: Performance Testing
```sql
-- Test query performance with new indexes
EXPLAIN ANALYZE
SELECT
    p.*,
    l.apartment_id,
    t.name
FROM payments p
JOIN leases l ON p.lease_id = l.id
JOIN tenants t ON l.responsible_tenant_id = t.id
WHERE p.status = 'overdue'
ORDER BY p.due_date;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Phase 6: Production Deployment (Week 6)

#### Step 6.1: Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Data validation complete
- [ ] Performance benchmarks met
- [ ] Backup created and verified
- [ ] Rollback plan documented
- [ ] Team notified of maintenance window

#### Step 6.2: Deployment Steps
```bash
# 1. Put application in maintenance mode
python manage.py maintenance_on

# 2. Create final backup
pg_dump -U postgres -d condominio -F custom -f prod_backup_$(date +%Y%m%d_%H%M%S).dump

# 3. Run migrations
python manage.py migrate

# 4. Verify migrations
python manage.py dbshell
> SELECT * FROM django_migrations ORDER BY applied DESC LIMIT 5;

# 5. Run post-migration validations
python manage.py validate_migration

# 6. Clear cache
python manage.py clear_cache

# 7. Restart application
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 8. Remove maintenance mode
python manage.py maintenance_off

# 9. Monitor logs
tail -f /var/log/condominio/app.log
```

## Rollback Plan

### Emergency Rollback Procedure
```bash
# 1. Stop application
sudo systemctl stop gunicorn

# 2. Restore database
pg_restore -U postgres -d condominio -c prod_backup_20250119_120000.dump

# 3. Revert code
git checkout previous_version_tag

# 4. Clear cache
redis-cli FLUSHALL

# 5. Restart application
sudo systemctl start gunicorn
sudo systemctl restart nginx
```

## Post-Implementation Tasks

### 1. Update Documentation
- [ ] Update API documentation
- [ ] Update database schema diagrams
- [ ] Update developer guide
- [ ] Create user training materials

### 2. Monitor System Health
```python
# monitoring/health_check.py

def check_database_health():
    checks = {
        'payments_table': check_table_exists('payments'),
        'pricing_table': check_table_exists('apartment_pricing'),
        'audit_enabled': check_audit_triggers(),
        'indexes_valid': check_index_health(),
        'no_orphans': check_referential_integrity()
    }

    return all(checks.values()), checks

def check_data_consistency():
    issues = []

    # Check for apartments without pricing
    orphan_apartments = Apartment.objects.filter(
        pricing_history__isnull=True
    )
    if orphan_apartments.exists():
        issues.append(f"{orphan_apartments.count()} apartments without pricing")

    # Check for leases without payments
    leases_no_payments = Lease.objects.filter(
        status='active',
        payments__isnull=True
    )
    if leases_no_payments.exists():
        issues.append(f"{leases_no_payments.count()} active leases without payments")

    return len(issues) == 0, issues
```

### 3. Performance Monitoring
```sql
-- Create monitoring views
CREATE VIEW v_database_metrics AS
SELECT
    'Total Payments' as metric,
    COUNT(*) as value
FROM payments
UNION ALL
SELECT
    'Overdue Payments',
    COUNT(*)
FROM payments
WHERE status = 'overdue'
UNION ALL
SELECT
    'Monthly Revenue',
    SUM(amount_paid)
FROM payments
WHERE paid_date >= DATE_TRUNC('month', CURRENT_DATE);

-- Schedule regular vacuum
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
    'vacuum-tables',
    '0 2 * * *',
    $$VACUUM ANALYZE payments, leases, apartments;$$
);
```

## Success Metrics

### Key Performance Indicators
1. **Query Performance**: 40% reduction in average query time
2. **Data Consistency**: Zero duplicate or conflicting records
3. **Audit Coverage**: 100% of critical operations logged
4. **Payment Tracking**: All active leases have payment records
5. **System Availability**: 99.9% uptime during migration

### Validation Queries
```sql
-- KPI Dashboard
SELECT
    'Query Performance' as kpi,
    AVG(mean_time) as value,
    'ms' as unit
FROM pg_stat_statements
WHERE query LIKE '%payments%'
UNION ALL
SELECT
    'Data Consistency',
    COUNT(*),
    'issues'
FROM (
    SELECT a.id
    FROM apartments a
    JOIN leases l ON a.id = l.apartment_id
    WHERE a.rental_value != l.rental_value
) issues
UNION ALL
SELECT
    'Audit Coverage',
    COUNT(DISTINCT table_name),
    'tables'
FROM audit_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '1 day';
```

## Support and Troubleshooting

### Common Issues and Solutions

#### Issue 1: Migration Fails
```bash
# Check migration status
python manage.py showmigrations

# Reset specific migration
python manage.py migrate core 0002_lease_number_of_tenants

# Fake migration if already applied manually
python manage.py migrate --fake core 0003_refactor_database
```

#### Issue 2: Performance Degradation
```sql
-- Rebuild indexes
REINDEX TABLE payments;
REINDEX TABLE apartment_pricing;

-- Update statistics
ANALYZE payments, apartment_pricing, leases;

-- Check for bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_dead_tup,
    n_live_tup,
    round(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

#### Issue 3: Data Inconsistency
```python
# management/commands/fix_data_consistency.py

from django.core.management.base import BaseCommand
from core.models import Apartment, ApartmentPricing, Lease

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Fix apartments without pricing
        for apartment in Apartment.objects.filter(pricing_history__isnull=True):
            ApartmentPricing.objects.create(
                apartment=apartment,
                rental_value=apartment.rental_value or Decimal('0.00'),
                cleaning_fee=apartment.cleaning_fee or Decimal('0.00'),
                effective_date=date.today(),
                is_current=True
            )
            self.stdout.write(f"Fixed pricing for apartment {apartment.id}")

        # Fix lease-tenant relationships
        for lease in Lease.objects.all():
            if not lease.lease_tenants.filter(is_responsible=True).exists():
                LeaseTenant.objects.create(
                    lease=lease,
                    tenant=lease.responsible_tenant,
                    is_responsible=True,
                    move_in_date=lease.start_date
                )
                self.stdout.write(f"Fixed responsible tenant for lease {lease.id}")
```

## Conclusion

This refactoring addresses critical database design issues and establishes a solid foundation for future growth. The new architecture provides:

1. **Eliminated Redundancy**: Single source of truth for all data
2. **Complete Audit Trail**: All changes tracked automatically
3. **Financial Visibility**: Comprehensive payment tracking
4. **Scalability**: Optimized for 10,000+ units
5. **Maintainability**: Clear separation of concerns

Follow this guide carefully, test thoroughly, and monitor closely during and after implementation.
