# Generated migration for database refactoring
# Run with: python manage.py migrate

from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator
from decimal import Decimal
import django.utils.timezone


def migrate_apartment_pricing(apps, schema_editor):
    """Migrate existing apartment pricing to new ApartmentPricing table"""
    Apartment = apps.get_model('core', 'Apartment')
    ApartmentPricing = apps.get_model('core', 'ApartmentPricing')

    for apartment in Apartment.objects.all():
        if apartment.rental_value:
            ApartmentPricing.objects.create(
                apartment=apartment,
                rental_value=apartment.rental_value,
                cleaning_fee=apartment.cleaning_fee or Decimal('0.00'),
                effective_date=apartment.lease_date or django.utils.timezone.now().date(),
                is_current=True
            )


def migrate_lease_tenants(apps, schema_editor):
    """Migrate tenant relationships to new junction table"""
    Lease = apps.get_model('core', 'Lease')
    LeaseTenant = apps.get_model('core', 'LeaseTenant')

    for lease in Lease.objects.all():
        # Create entry for responsible tenant
        if lease.responsible_tenant:
            LeaseTenant.objects.create(
                lease=lease,
                tenant=lease.responsible_tenant,
                is_responsible=True,
                move_in_date=lease.start_date,
                tag_deposit_paid=lease.responsible_tenant.tag_deposit_paid,
                tag_deposit_amount=lease.tag_fee
            )

        # Create entries for other tenants
        for tenant in lease.tenants.all():
            if tenant != lease.responsible_tenant:
                LeaseTenant.objects.create(
                    lease=lease,
                    tenant=tenant,
                    is_responsible=False,
                    move_in_date=lease.start_date
                )


def create_initial_payments(apps, schema_editor):
    """Create initial payment records for active leases"""
    Lease = apps.get_model('core', 'Lease')
    Payment = apps.get_model('core', 'Payment')
    from datetime import date
    from dateutil.relativedelta import relativedelta

    current_month_start = date.today().replace(day=1)

    for lease in Lease.objects.all():
        # Create current month payment if not exists
        if not Payment.objects.filter(
            lease=lease,
            reference_month=current_month_start,
            payment_category='rent'
        ).exists():
            due_date = current_month_start.replace(day=min(lease.due_day, 28))

            Payment.objects.create(
                lease=lease,
                payment_category='rent',
                amount_due=lease.rental_value,
                due_date=due_date,
                reference_month=current_month_start,
                status='pending' if due_date >= date.today() else 'overdue'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_lease_number_of_tenants'),  # Update with your last migration
    ]

    operations = [
        # =============================================
        # Step 1: Add new status field to Lease
        # =============================================
        migrations.AddField(
            model_name='lease',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('pending_signature', 'Pending Signature'),
                    ('active', 'Active'),
                    ('ending_soon', 'Ending Soon'),
                    ('expired', 'Expired'),
                    ('terminated', 'Terminated'),
                    ('renewed', 'Renewed')
                ],
                default='active',
                max_length=20
            ),
        ),

        migrations.AddField(
            model_name='lease',
            name='lease_number',
            field=models.CharField(max_length=50, unique=True, null=True),
        ),

        migrations.AddField(
            model_name='lease',
            name='end_date',
            field=models.DateField(null=True, blank=True),
        ),

        migrations.AddField(
            model_name='lease',
            name='actual_end_date',
            field=models.DateField(null=True, blank=True, help_text='For early terminations'),
        ),

        # =============================================
        # Step 2: Create ApartmentPricing model
        # =============================================
        migrations.CreateModel(
            name='ApartmentPricing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('rental_value', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    validators=[MinValueValidator(Decimal('0.00'))]
                )),
                ('cleaning_fee', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10
                )),
                ('condominium_fee', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10
                )),
                ('iptu_value', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10
                )),
                ('effective_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=False)),
                ('reason', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('apartment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pricing_history',
                    to='core.apartment'
                )),
            ],
            options={
                'ordering': ['-effective_date'],
                'indexes': [
                    models.Index(fields=['apartment', 'is_current'], name='idx_apartment_current_price'),
                    models.Index(fields=['apartment', 'effective_date'], name='idx_apartment_price_dates'),
                ],
            },
        ),

        migrations.AddConstraint(
            model_name='apartmentpricing',
            constraint=models.UniqueConstraint(
                fields=['apartment', 'is_current'],
                condition=models.Q(is_current=True),
                name='unique_current_price_per_apartment'
            ),
        ),

        # =============================================
        # Step 3: Create Payment model
        # =============================================
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('payment_category', models.CharField(
                    choices=[
                        ('rent', 'Rent'),
                        ('cleaning', 'Cleaning Fee'),
                        ('deposit', 'Security Deposit'),
                        ('late_fee', 'Late Fee'),
                        ('damage', 'Damage'),
                        ('utility', 'Utility'),
                        ('other', 'Other')
                    ],
                    max_length=20
                )),
                ('amount_due', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    validators=[MinValueValidator(Decimal('0.01'))]
                )),
                ('amount_paid', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10
                )),
                ('discount_amount', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10
                )),
                ('late_fee_amount', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10
                )),
                ('due_date', models.DateField()),
                ('paid_date', models.DateField(blank=True, null=True)),
                ('reference_month', models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('partial', 'Partially Paid'),
                        ('paid', 'Paid'),
                        ('overdue', 'Overdue'),
                        ('cancelled', 'Cancelled'),
                        ('refunded', 'Refunded')
                    ],
                    default='pending',
                    max_length=20
                )),
                ('payment_method', models.CharField(
                    blank=True,
                    choices=[
                        ('cash', 'Cash'),
                        ('check', 'Check'),
                        ('transfer', 'Bank Transfer'),
                        ('pix', 'PIX'),
                        ('credit_card', 'Credit Card'),
                        ('debit_card', 'Debit Card'),
                        ('deposit', 'Deposit'),
                        ('other', 'Other')
                    ],
                    max_length=50,
                    null=True
                )),
                ('transaction_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_name', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('receipt_number', models.CharField(blank=True, max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('lease', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to='core.lease'
                )),
            ],
            options={
                'ordering': ['-due_date', '-created_at'],
                'indexes': [
                    models.Index(fields=['lease', 'status', 'due_date'], name='idx_payment_lease_status'),
                    models.Index(fields=['due_date', 'status'], name='idx_payment_due_status'),
                    models.Index(fields=['reference_month'], name='idx_payment_ref_month'),
                ],
            },
        ),

        # =============================================
        # Step 4: Create Document model
        # =============================================
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('document_type', models.CharField(
                    choices=[
                        ('contract', 'Contract'),
                        ('addendum', 'Addendum'),
                        ('receipt', 'Receipt'),
                        ('notice', 'Notice'),
                        ('warning', 'Warning'),
                        ('inspection', 'Inspection Report'),
                        ('invoice', 'Invoice'),
                        ('photo', 'Photo'),
                        ('other', 'Other')
                    ],
                    max_length=50
                )),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('file_path', models.CharField(max_length=500)),
                ('file_name', models.CharField(max_length=255)),
                ('file_size', models.IntegerField(blank=True, null=True)),
                ('file_type', models.CharField(blank=True, max_length=50, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=100, null=True)),
                ('file_hash', models.CharField(blank=True, max_length=64, null=True)),
                ('version', models.IntegerField(default=1)),
                ('is_latest_version', models.BooleanField(default=True)),
                ('requires_signatures', models.BooleanField(default=False)),
                ('tenant_signed', models.BooleanField(default=False)),
                ('tenant_signed_at', models.DateTimeField(blank=True, null=True)),
                ('landlord_signed', models.BooleanField(default=False)),
                ('landlord_signed_at', models.DateTimeField(blank=True, null=True)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('archived_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('lease', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='core.lease'
                )),
                ('tenant', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='core.tenant'
                )),
                ('apartment', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='core.apartment'
                )),
                ('payment', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to='core.payment'
                )),
                ('parent_document', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='versions',
                    to='core.document'
                )),
            ],
            options={
                'ordering': ['-generated_at'],
                'indexes': [
                    models.Index(fields=['lease', 'document_type'], name='idx_doc_lease_type'),
                    models.Index(fields=['tenant', 'document_type'], name='idx_doc_tenant_type'),
                ],
            },
        ),

        # =============================================
        # Step 5: Create Expense model
        # =============================================
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('expense_type', models.CharField(
                    choices=[
                        ('maintenance', 'Maintenance'),
                        ('repair', 'Repair'),
                        ('tax', 'Tax'),
                        ('insurance', 'Insurance'),
                        ('utility', 'Utility'),
                        ('cleaning', 'Cleaning'),
                        ('management', 'Management'),
                        ('legal', 'Legal'),
                        ('other', 'Other')
                    ],
                    max_length=30
                )),
                ('description', models.TextField()),
                ('amount', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    validators=[MinValueValidator(Decimal('0.01'))]
                )),
                ('expense_date', models.DateField()),
                ('payment_date', models.DateField(blank=True, null=True)),
                ('vendor_name', models.CharField(blank=True, max_length=200, null=True)),
                ('vendor_document', models.CharField(blank=True, max_length=20, null=True)),
                ('vendor_phone', models.CharField(blank=True, max_length=20, null=True)),
                ('invoice_number', models.CharField(blank=True, max_length=100, null=True)),
                ('is_recurring', models.BooleanField(default=False)),
                ('recurrence_pattern', models.CharField(
                    blank=True,
                    choices=[
                        ('monthly', 'Monthly'),
                        ('bimonthly', 'Bimonthly'),
                        ('quarterly', 'Quarterly'),
                        ('semiannual', 'Semiannual'),
                        ('yearly', 'Yearly')
                    ],
                    max_length=20,
                    null=True
                )),
                ('recurrence_day', models.IntegerField(blank=True, null=True)),
                ('next_recurrence_date', models.DateField(blank=True, null=True)),
                ('recurrence_end_date', models.DateField(blank=True, null=True)),
                ('requires_approval', models.BooleanField(default=False)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('approval_notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('building', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expenses',
                    to='core.building'
                )),
                ('apartment', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expenses',
                    to='core.apartment'
                )),
            ],
            options={
                'ordering': ['-expense_date', '-created_at'],
                'indexes': [
                    models.Index(fields=['building', 'expense_date'], name='idx_expense_building_date'),
                    models.Index(fields=['apartment', 'expense_date'], name='idx_expense_apartment_date'),
                ],
            },
        ),

        # =============================================
        # Step 6: Create LeaseTenant junction table
        # =============================================
        migrations.CreateModel(
            name='LeaseTenant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('is_responsible', models.BooleanField(default=False)),
                ('move_in_date', models.DateField(blank=True, null=True)),
                ('move_out_date', models.DateField(blank=True, null=True)),
                ('tag_number', models.CharField(blank=True, max_length=50, null=True)),
                ('tag_deposit_paid', models.BooleanField(default=False)),
                ('tag_deposit_amount', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=10,
                    null=True
                )),
                ('lease', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.lease'
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='core.tenant'
                )),
            ],
            options={
                'db_table': 'core_lease_tenants',
                'unique_together': {('lease', 'tenant')},
            },
        ),

        migrations.AddConstraint(
            model_name='leasetenant',
            constraint=models.UniqueConstraint(
                fields=['lease', 'is_responsible'],
                condition=models.Q(is_responsible=True),
                name='unique_responsible_tenant_per_lease'
            ),
        ),

        # =============================================
        # Step 7: Create AuditLog model
        # =============================================
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('table_name', models.CharField(max_length=50)),
                ('record_id', models.BigIntegerField()),
                ('action', models.CharField(
                    choices=[
                        ('INSERT', 'Insert'),
                        ('UPDATE', 'Update'),
                        ('DELETE', 'Delete'),
                        ('RESTORE', 'Restore'),
                        ('ARCHIVE', 'Archive')
                    ],
                    max_length=20
                )),
                ('old_values', models.JSONField(blank=True, null=True)),
                ('new_values', models.JSONField(blank=True, null=True)),
                ('changed_fields', models.JSONField(blank=True, null=True)),
                ('change_summary', models.TextField(blank=True, null=True)),
                ('user_name', models.CharField(blank=True, max_length=100, null=True)),
                ('user_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('session_id', models.CharField(blank=True, max_length=100, null=True)),
                ('request_id', models.CharField(blank=True, max_length=50, null=True)),
                ('api_endpoint', models.CharField(blank=True, max_length=200, null=True)),
                ('http_method', models.CharField(blank=True, max_length=10, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['table_name', 'record_id', '-created_at'], name='idx_audit_table_record'),
                    models.Index(fields=['-created_at'], name='idx_audit_timestamp'),
                ],
            },
        ),

        # =============================================
        # Step 8: Run data migrations
        # =============================================
        migrations.RunPython(migrate_apartment_pricing, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(migrate_lease_tenants, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(create_initial_payments, reverse_code=migrations.RunPython.noop),
    ]