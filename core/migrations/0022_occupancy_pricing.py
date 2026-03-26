from decimal import Decimal

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


def populate_occupancy_pricing(apps, schema_editor):
    Apartment = apps.get_model("core", "Apartment")
    Lease = apps.get_model("core", "Lease")

    # For apartments with max_tenants == 2: set rental_value_double = rental_value + 100
    for apartment in Apartment._default_manager.filter(max_tenants=2).iterator():
        apartment.rental_value_double = apartment.rental_value + Decimal("100.00")
        apartment.save(update_fields=["rental_value_double"])

    # For all leases: set rental_value = apartment.rental_value
    # Special case: building 850, apartment 203 → rental_value = 1500, number_of_tenants = 2
    for lease in Lease._default_manager.select_related("apartment__building").iterator():
        apartment = lease.apartment
        building = apartment.building
        if building.street_number == "850" and apartment.number == 203:
            lease.rental_value = Decimal("1500.00")
            lease.number_of_tenants = 2
            lease.save(update_fields=["rental_value", "number_of_tenants"])
        else:
            lease.rental_value = apartment.rental_value
            lease.save(update_fields=["rental_value"])


def reverse_occupancy_pricing(apps, schema_editor):
    Lease = apps.get_model("core", "Lease")
    Lease._default_manager.update(rental_value=None)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0021_person_initial_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="apartment",
            name="rental_value_double",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Valor do aluguel para 2 pessoas",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AddField(
            model_name="dependent",
            name="cpf_cnpj",
            field=models.CharField(
                blank=True,
                default="",
                help_text="CPF ou CNPJ do dependente",
                max_length=14,
            ),
        ),
        migrations.AddField(
            model_name="lease",
            name="resident_dependent",
            field=models.ForeignKey(
                blank=True,
                help_text="Dependente que reside no apartamento neste contrato",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="leases_as_resident",
                to="core.dependent",
            ),
        ),
        migrations.AddField(
            model_name="lease",
            name="rental_value",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Valor do aluguel acordado no contrato",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
            ),
        ),
        migrations.AlterField(
            model_name="lease",
            name="number_of_tenants",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Número de ocupantes (1 ou 2). Determina tier de preço. Deve ser <= apartment.max_tenants.",
            ),
        ),
        migrations.RunPython(populate_occupancy_pricing, reverse_occupancy_pricing),
        migrations.AlterField(
            model_name="lease",
            name="rental_value",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Valor do aluguel acordado no contrato",
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
            ),
        ),
    ]
