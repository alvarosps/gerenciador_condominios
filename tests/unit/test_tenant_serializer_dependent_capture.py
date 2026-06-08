"""Unit tests for TenantSerializer dependent capture + audit propagation (onboarding G1/G4).

After save, the serializer must expose the created Dependents on `tenant._created_dependents`
in the same order they were supplied (the model has no Meta.ordering, so a later session resolves
the resident dependent by input index). It must also propagate created_by/updated_by from the
save() kwargs onto each nested Dependent.
"""

import pytest

from core.models import Dependent
from core.serializers import TenantSerializer


def _tenant_payload(dependents=None):
    payload = {
        "name": "Inquilino Captura",
        "cpf_cnpj": "71286955084",
        "is_company": False,
        "phone": "11966660001",
        "marital_status": "Solteiro(a)",
        "profession": "Engenheiro",
        "due_day": 10,
    }
    if dependents is not None:
        payload["dependents"] = dependents
    return payload


@pytest.mark.unit
@pytest.mark.django_db
class TestTenantSerializerDependentCapture:
    def test_create_captures_dependents_in_input_order_with_audit(self, admin_user):
        d1 = {"name": "Dependente Um", "phone": "11966660011", "cpf_cnpj": ""}
        d2 = {"name": "Dependente Dois", "phone": "11966660012", "cpf_cnpj": ""}

        serializer = TenantSerializer(data=_tenant_payload(dependents=[d1, d2]))
        assert serializer.is_valid() is True, serializer.errors
        tenant = serializer.save(created_by=admin_user, updated_by=admin_user)

        created = tenant._created_dependents
        assert [dep.name for dep in created] == ["Dependente Um", "Dependente Dois"]
        assert all(isinstance(dep, Dependent) for dep in created)
        for dep in created:
            assert dep.created_by == admin_user
            assert dep.updated_by == admin_user

    def test_create_without_dependents_yields_empty_list(self, admin_user):
        serializer = TenantSerializer(data=_tenant_payload())
        assert serializer.is_valid() is True, serializer.errors
        tenant = serializer.save(created_by=admin_user, updated_by=admin_user)

        assert tenant._created_dependents == []

    def test_create_without_audit_kwargs_leaves_dependent_audit_none(self):
        d1 = {"name": "Dependente Sem Audit", "phone": "11966660013", "cpf_cnpj": ""}

        serializer = TenantSerializer(data=_tenant_payload(dependents=[d1]))
        assert serializer.is_valid() is True, serializer.errors
        tenant = serializer.save()

        created = tenant._created_dependents
        assert len(created) == 1
        assert created[0].created_by is None
        assert created[0].updated_by is None
