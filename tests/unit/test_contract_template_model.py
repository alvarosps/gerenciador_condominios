"""Unit tests for the ContractTemplate model (DB-backed contract template versions)."""

import pytest
from django.db import connection

from core.models import ContractTemplate


@pytest.fixture
def default_template(admin_user):
    """Replace the migration-seeded DEFAULT with a small, known one for deterministic tests."""
    ContractTemplate.objects.all().delete()
    return ContractTemplate.objects.create(
        content="<html><body>Padrão {{ tenant }}</body></html>",
        label="Padrão",
        is_default=True,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.unit
class TestGetActiveContent:
    def test_returns_active_content(self, default_template):
        assert ContractTemplate.get_active_content() == default_template.content

    def test_returns_newest_active_after_save(self, default_template, admin_user):
        ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        assert ContractTemplate.get_active_content() == "<html>v2 {{ tenant }}</html>"

    def test_raises_when_no_active_template(self, default_template):
        ContractTemplate.objects.all().delete()
        with pytest.raises(ContractTemplate.DoesNotExist):
            ContractTemplate.get_active_content()


@pytest.mark.unit
class TestSaveVersion:
    def test_creates_new_active_version(self, default_template, admin_user):
        version = ContractTemplate.save_version("<html>new {{ tenant }}</html>", user=admin_user)
        assert version.is_active is True
        assert version.is_default is False
        assert version.content == "<html>new {{ tenant }}</html>"

    def test_deactivates_previous_active(self, default_template, admin_user):
        ContractTemplate.save_version("<html>new {{ tenant }}</html>", user=admin_user)
        default_template.refresh_from_db()
        assert default_template.is_active is False

    def test_exactly_one_active_after_save(self, default_template, admin_user):
        ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        ContractTemplate.save_version("<html>v3 {{ tenant }}</html>", user=admin_user)
        assert ContractTemplate.objects.filter(is_active=True).count() == 1

    def test_label_is_a_readable_timestamp(self, default_template, admin_user):
        version = ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        # A non-empty, non-"Padrão" label (timestamp); distinct from the default.
        assert version.label
        assert version.label != "Padrão"

    def test_invalid_jinja_raises_and_creates_no_version(self, default_template, admin_user):
        before = ContractTemplate.objects.count()
        with pytest.raises(ValueError, match="Template inválido"):
            ContractTemplate.save_version("<html>{% if %}</html>", user=admin_user)
        assert ContractTemplate.objects.count() == before
        # The previously active template must remain active and unchanged.
        default_template.refresh_from_db()
        assert default_template.is_active is True

    def test_invalid_jinja_message_includes_line_number(self, default_template, admin_user):
        with pytest.raises(ValueError, match="linha"):
            ContractTemplate.save_version("<html>{% endfor %}</html>", user=admin_user)

    def test_empty_content_raises(self, default_template, admin_user):
        with pytest.raises(ValueError, match="vazio"):
            ContractTemplate.save_version("   \n\t ", user=admin_user)


@pytest.mark.unit
class TestRotation:
    def test_keeps_default_active_and_n_recent(self, default_template, admin_user):
        # Create more than the retention window of extra versions.
        total_extra = ContractTemplate.MAX_RETAINED_VERSIONS + 5
        for i in range(total_extra):
            ContractTemplate.save_version(f"<html>v{i} {{{{ tenant }}}}</html>", user=admin_user)

        templates = list(ContractTemplate.objects.all())

        # DEFAULT must survive.
        assert any(t.is_default for t in templates)
        # The current active must survive.
        assert sum(1 for t in templates if t.is_active) == 1
        # Total = DEFAULT + retained recent versions (the active one is among the recent).
        assert len(templates) == ContractTemplate.MAX_RETAINED_VERSIONS + 1

    def test_oldest_non_default_versions_deleted(self, default_template, admin_user):
        first_extra = ContractTemplate.save_version(
            "<html>oldest {{ tenant }}</html>", user=admin_user
        )
        for i in range(ContractTemplate.MAX_RETAINED_VERSIONS + 2):
            ContractTemplate.save_version(f"<html>v{i} {{{{ tenant }}}}</html>", user=admin_user)

        assert not ContractTemplate.objects.filter(pk=first_extra.pk).exists()

    def test_rotation_never_deletes_default(self, default_template, admin_user):
        for i in range(ContractTemplate.MAX_RETAINED_VERSIONS + 10):
            ContractTemplate.save_version(f"<html>v{i} {{{{ tenant }}}}</html>", user=admin_user)
        assert ContractTemplate.objects.filter(pk=default_template.pk).exists()


@pytest.mark.unit
class TestRestoreVersion:
    def test_restore_activates_target_version(self, default_template, admin_user):
        version = ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        # default is now inactive, version is active. Restore the default.
        ContractTemplate.restore_version(default_template.pk, user=admin_user)

        default_template.refresh_from_db()
        version.refresh_from_db()
        assert default_template.is_active is True
        assert version.is_active is False

    def test_restore_keeps_exactly_one_active(self, default_template, admin_user):
        ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        ContractTemplate.restore_version(default_template.pk, user=admin_user)
        assert ContractTemplate.objects.filter(is_active=True).count() == 1

    def test_restore_makes_active_content_match_target(self, default_template, admin_user):
        ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        ContractTemplate.restore_version(default_template.pk, user=admin_user)
        assert ContractTemplate.get_active_content() == default_template.content

    def test_restore_nonexistent_id_raises(self, default_template, admin_user):
        with pytest.raises(ContractTemplate.DoesNotExist):
            ContractTemplate.restore_version(999999, user=admin_user)


@pytest.mark.unit
class TestListVersions:
    def test_default_listed_first(self, default_template, admin_user):
        ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        versions = list(ContractTemplate.list_versions())
        assert versions[0].is_default is True

    def test_remaining_sorted_newest_first(self, default_template, admin_user):
        v2 = ContractTemplate.save_version("<html>v2 {{ tenant }}</html>", user=admin_user)
        v3 = ContractTemplate.save_version("<html>v3 {{ tenant }}</html>", user=admin_user)
        versions = list(ContractTemplate.list_versions())
        # versions[0] == default; the rest are newest-first.
        non_default = versions[1:]
        assert non_default[0].pk == v3.pk
        assert non_default[1].pk == v2.pk


@pytest.mark.unit
class TestRowLevelSecurity:
    def test_rls_enabled_on_table(self, default_template):
        """Migration enables RLS on public.core_contracttemplate (Supabase rule)."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = 'core_contracttemplate'"
            )
            row = cursor.fetchone()
        assert row is not None
        assert row[0] is True
