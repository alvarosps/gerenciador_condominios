# Data migration: copy fields between models + rename rent_due_day -> due_day

from django.db import migrations, models

from core.validators import validate_due_day


def migrate_data_forward(apps, schema_editor):
    Lease = apps.get_model("core", "Lease")
    Tenant = apps.get_model("core", "Tenant")
    Apartment = apps.get_model("core", "Apartment")

    # 1. Lease -> Tenant: warning_count (aggregate MAX across all leases including soft-deleted)
    from django.db.models import Max

    tenant_warnings = Lease._default_manager.values("responsible_tenant_id").annotate(
        max_warnings=Max("warning_count")
    )
    for entry in tenant_warnings:
        Tenant._default_manager.filter(pk=entry["responsible_tenant_id"]).update(
            warning_count=entry["max_warnings"]
        )

    # 2. Tenant -> Lease: deposit_amount, cleaning_fee_paid, tag_deposit_paid
    for lease in Lease._default_manager.select_related("responsible_tenant").iterator():
        tenant = lease.responsible_tenant
        lease.deposit_amount = tenant.deposit_amount
        lease.cleaning_fee_paid = tenant.cleaning_fee_paid
        lease.tag_deposit_paid = tenant.tag_deposit_paid
        lease.save(update_fields=["deposit_amount", "cleaning_fee_paid", "tag_deposit_paid"])

    # 3. Sync is_rented (only active leases)
    Apartment._default_manager.update(is_rented=False)
    active_apartment_ids = Lease._default_manager.filter(is_deleted=False).values_list(
        "apartment_id", flat=True
    )
    Apartment._default_manager.filter(pk__in=active_apartment_ids).update(is_rented=True)


def migrate_data_reverse(apps, schema_editor):
    Lease = apps.get_model("core", "Lease")
    Tenant = apps.get_model("core", "Tenant")

    # Reverse: Lease -> Tenant: deposit_amount, cleaning_fee_paid, tag_deposit_paid
    for lease in Lease._default_manager.select_related("responsible_tenant").iterator():
        tenant = lease.responsible_tenant
        tenant.deposit_amount = lease.deposit_amount
        tenant.cleaning_fee_paid = lease.cleaning_fee_paid
        tenant.tag_deposit_paid = lease.tag_deposit_paid
        tenant.save(update_fields=["deposit_amount", "cleaning_fee_paid", "tag_deposit_paid"])

    # Reverse: Tenant -> Lease: warning_count (copy back to most recent lease)
    for tenant in Tenant._default_manager.iterator():
        Lease._default_manager.filter(responsible_tenant=tenant).order_by("-start_date").update(
            warning_count=tenant.warning_count
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_add_new_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_data_forward, migrate_data_reverse),
        migrations.RenameField(
            model_name="tenant",
            old_name="rent_due_day",
            new_name="due_day",
        ),
        migrations.AlterField(
            model_name="tenant",
            name="due_day",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Dia do vencimento do aluguel",
                validators=[validate_due_day],
            ),
        ),
    ]
