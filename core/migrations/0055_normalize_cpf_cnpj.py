"""Normalize CPF/CNPJ to digits-only for Tenant, Landlord and Dependent.

Runs BEFORE 0056 adds the partial unique constraint on Tenant.cpf_cnpj, so the
normalized (collision-free) values are in place when the constraint is enforced.

Existing rows held a mix of formatted ("123.456.789-01") and raw ("12345678901")
documents, which made the same person look like two identities and broke the
WhatsApp login for the raw-format rows. After this migration every document is
digits-only.

Collision detection: if two ACTIVE tenants normalize to the same digits the
migration aborts with RuntimeError (the operator resolves the duplicate manually
and re-runs) — it never picks one arbitrarily. A collision between an active and a
soft-deleted tenant is tolerated (the partial constraint only covers active rows).
"""

import re

from django.db import migrations

_NON_DIGITS = re.compile(r"[^0-9]")


def _normalize(value: str) -> str:
    return _NON_DIGITS.sub("", value or "")


def normalize_documents(apps, schema_editor):
    # _base_manager: historical models don't carry the custom SoftDeleteManager, and the base
    # manager reaches soft-deleted rows too (normalizing all keeps the table coherent).
    tenant_model = apps.get_model("core", "Tenant")

    # Abort before writing if two ACTIVE tenants would collide after normalization.
    seen: dict[str, int] = {}
    collisions: list[str] = []
    for tenant in tenant_model._base_manager.filter(is_deleted=False).only("id", "cpf_cnpj"):
        cleaned = _normalize(tenant.cpf_cnpj)
        if not cleaned:
            continue
        if cleaned in seen:
            collisions.append(f"{cleaned} (tenants #{seen[cleaned]} and #{tenant.id})")
        else:
            seen[cleaned] = tenant.id
    if collisions:
        joined = "; ".join(collisions)
        msg = (
            "Cannot normalize CPF/CNPJ: active tenants collide after stripping formatting "
            f"-> {joined}. Resolve the duplicates manually and re-run the migration."
        )
        raise RuntimeError(msg)

    # Write normalized values only when they differ (idempotent).
    for model_name in ("Tenant", "Landlord", "Dependent"):
        model = apps.get_model("core", model_name)
        for row in model._base_manager.exclude(cpf_cnpj="").only("id", "cpf_cnpj"):
            cleaned = _normalize(row.cpf_cnpj)
            if cleaned != row.cpf_cnpj:
                model._base_manager.filter(pk=row.pk).update(cpf_cnpj=cleaned)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0054_financialsettings_default_city"),
    ]

    operations = [
        migrations.RunPython(normalize_documents, migrations.RunPython.noop),
    ]
