# Seed the DEFAULT contract template row from the canonical on-disk file
# (core/templates/contract_template.html). The file remains in git as the seed source;
# from now on the durable source of truth is the database (ephemeral-FS safe on Render).
#
# Idempotent: only creates the DEFAULT when no ContractTemplate exists yet.

from pathlib import Path

from django.conf import settings
from django.db import migrations

DEFAULT_TEMPLATE_LABEL = "Padrão"


def seed_default_template(apps, schema_editor):
    """Create the DEFAULT/active template row from the on-disk template, if absent."""
    ContractTemplate = apps.get_model("core", "ContractTemplate")

    # Historical models expose the recorded managers; ContractTemplate has only the
    # default manager (no soft delete), which sees every row.
    if ContractTemplate.objects.exists():
        return

    template_path = (
        Path(settings.BASE_DIR) / "core" / "templates" / "contract_template.html"
    )
    content = template_path.read_text(encoding="utf-8")

    ContractTemplate.objects.create(
        content=content,
        label=DEFAULT_TEMPLATE_LABEL,
        is_active=True,
        is_default=True,
    )


def remove_default_template(apps, schema_editor):
    """Reverse: drop the seeded DEFAULT row (only the seed, by its label/flag)."""
    ContractTemplate = apps.get_model("core", "ContractTemplate")
    ContractTemplate.objects.filter(is_default=True, label=DEFAULT_TEMPLATE_LABEL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_contract_template"),
    ]

    operations = [
        migrations.RunPython(seed_default_template, reverse_code=remove_default_template),
    ]
