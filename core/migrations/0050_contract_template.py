# Creates the DB-backed, versioned ContractTemplate model and enables Row Level
# Security on its public table in the SAME migration (Supabase rule — see
# core/migrations/0047_enable_row_level_security.py). RLS-enabled-no-policy denies the
# Data API roles while the Django backend (postgres role, rolbypassrls=true) is unaffected.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

# Static SQL (no f-strings → no ruff S608); ENABLE on an already-enabled table is a no-op.
ENABLE_CONTRACT_TEMPLATE_RLS = (
    "ALTER TABLE public.core_contracttemplate ENABLE ROW LEVEL SECURITY;"
)
DISABLE_CONTRACT_TEMPLATE_RLS = (
    "ALTER TABLE public.core_contracttemplate DISABLE ROW LEVEL SECURITY;"
)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_alter_notification_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContractTemplate",
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
                    "content",
                    models.TextField(help_text="Conteúdo HTML do template de contrato"),
                ),
                (
                    "label",
                    models.CharField(
                        help_text="Rótulo legível da versão (ex.: 'Padrão' ou um timestamp)",
                        max_length=100,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="Versão atualmente em uso para gerar contratos (exatamente uma)",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="Versão original/seed do template (para restaurar o padrão)",
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
                "verbose_name": "Template de Contrato",
                "verbose_name_plural": "Templates de Contrato",
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunSQL(
            sql=ENABLE_CONTRACT_TEMPLATE_RLS,
            reverse_sql=DISABLE_CONTRACT_TEMPLATE_RLS,
        ),
    ]
