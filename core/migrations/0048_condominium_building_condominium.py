# Phased, PROD-safe migration (design §13, §14 Phase 1a):
#   1. Create the Condominium tenancy-root model.
#   2. Enable RLS on the new public.core_condominium table (Supabase rule —
#      see core/migrations/0047_enable_row_level_security.py).
#   3. Add Building.condominium as nullable (no default needed).
#   4. Data-migration: create the single default Condominium and backfill every
#      Building (including soft-deleted rows) to point at it — idempotent.
#   5. Flip Building.condominium to non-null.
#
# Forward and backward are both clean; the backfill is idempotent.

import django.db.models.deletion
import django.db.models.manager
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

from core.models import DEFAULT_CONDOMINIUM_NAME

# Static SQL (no f-strings → no ruff S608); ENABLE on an already-enabled table is a no-op.
ENABLE_CONDOMINIUM_RLS = "ALTER TABLE public.core_condominium ENABLE ROW LEVEL SECURITY;"
DISABLE_CONDOMINIUM_RLS = "ALTER TABLE public.core_condominium DISABLE ROW LEVEL SECURITY;"


def create_default_and_backfill(apps, schema_editor):
    """Create the default Condominium and backfill all buildings (idempotent)."""
    Condominium = apps.get_model("core", "Condominium")
    Building = apps.get_model("core", "Building")
    # Historical models only carry the recorded managers; _default_manager is the
    # first-declared plain Manager (all_objects), which sees every row — including
    # soft-deleted ones, so no condominium_id stays null before the non-null flip.
    default_condominium, _ = Condominium._default_manager.get_or_create(
        name=DEFAULT_CONDOMINIUM_NAME,
        defaults={"notes": ""},
    )
    Building._default_manager.filter(condominium__isnull=True).update(
        condominium=default_condominium
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0047_enable_row_level_security"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Condominium",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="Data/hora de criação do registro",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="Data/hora da última modificação",
                    ),
                ),
                (
                    "is_deleted",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        editable=False,
                        help_text="Indica se o registro foi excluído",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        editable=False,
                        help_text="Data/hora da exclusão",
                        null=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Nome do condomínio", max_length=100),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, default="", help_text="Observações internas"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        help_text="Usuário que criou o registro",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        help_text="Usuário que excluiu o registro",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        help_text="Usuário que modificou o registro",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.RunSQL(
            sql=ENABLE_CONDOMINIUM_RLS,
            reverse_sql=DISABLE_CONDOMINIUM_RLS,
        ),
        migrations.AddField(
            model_name="building",
            name="condominium",
            field=models.ForeignKey(
                blank=True,
                help_text="Condomínio ao qual o prédio pertence",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="buildings",
                to="core.condominium",
            ),
        ),
        migrations.RunPython(
            create_default_and_backfill,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="building",
            name="condominium",
            field=models.ForeignKey(
                blank=True,
                help_text="Condomínio ao qual o prédio pertence",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="buildings",
                to="core.condominium",
            ),
        ),
    ]
