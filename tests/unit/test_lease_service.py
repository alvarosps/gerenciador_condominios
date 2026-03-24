"""Unit tests for core/services/lease_service.py."""

import pytest
from django.contrib.auth import get_user_model

from core.models import Apartment, Building, Lease, Tenant
from core.services.lease_service import terminate_lease, transfer_lease

User = get_user_model()


@pytest.fixture
def building(sample_building_data):
    return Building.objects.create(**sample_building_data)


@pytest.fixture
def old_apt(building):
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=1000,
        cleaning_fee=100,
        max_tenants=2,
    )


@pytest.fixture
def new_apt(building):
    return Apartment.objects.create(
        building=building,
        number=102,
        rental_value=1200,
        cleaning_fee=100,
        max_tenants=2,
    )


@pytest.fixture
def tenant():
    return Tenant.objects.create(
        name="João da Silva",
        cpf_cnpj="529.982.247-25",
        phone="(11) 98765-4321",
        marital_status="Casado(a)",
        profession="Engenheiro",
        due_day=10,
    )


@pytest.fixture
def second_tenant():
    return Tenant.objects.create(
        name="Maria Souza",
        cpf_cnpj="71286955084",
        phone="(11) 97654-3210",
        marital_status="Solteiro(a)",
        profession="Médica",
        due_day=10,
    )


@pytest.fixture
def staff_user():
    return User.objects.create_user(username="admin_lease", password="pass", is_staff=True)


@pytest.fixture
def active_lease(old_apt, tenant):
    lease = Lease.objects.create(
        apartment=old_apt,
        responsible_tenant=tenant,
        start_date="2026-01-01",
        validity_months=12,
        tag_fee=50,
        contract_generated=True,
        contract_signed=True,
        interfone_configured=True,
    )
    lease.tenants.add(tenant)
    return lease


class TestTerminateLease:
    def test_terminate_soft_deletes_lease(self, active_lease, staff_user):
        terminate_lease(active_lease.id, staff_user)

        active_lease.refresh_from_db()
        assert active_lease.is_deleted is True

    def test_terminate_resets_contract_flags(self, active_lease, staff_user):
        terminate_lease(active_lease.id, staff_user)

        active_lease.refresh_from_db()
        assert active_lease.contract_generated is False
        assert active_lease.contract_signed is False
        assert active_lease.interfone_configured is False

    def test_terminate_marks_apartment_available(self, active_lease, old_apt, staff_user):
        terminate_lease(active_lease.id, staff_user)

        old_apt.refresh_from_db()
        assert old_apt.is_rented is False

    def test_terminate_sets_deleted_by(self, active_lease, staff_user):
        terminate_lease(active_lease.id, staff_user)

        active_lease.refresh_from_db()
        assert active_lease.deleted_by == staff_user

    def test_terminate_nonexistent_lease_raises(self, staff_user):
        with pytest.raises(Lease.DoesNotExist):
            terminate_lease(99999, staff_user)


class TestTransferLease:
    def test_transfer_creates_new_lease_on_target_apartment(
        self, active_lease, new_apt, tenant, staff_user
    ):
        new_lease = transfer_lease(
            lease_id=active_lease.id,
            payload={
                "apartment_id": new_apt.id,
                "responsible_tenant_id": tenant.id,
                "tenant_ids": [tenant.id],
                "start_date": "2026-01-01",
                "validity_months": 12,
                "tag_fee": 50,
            },
            user=staff_user,
        )

        assert new_lease.apartment_id == new_apt.id
        assert new_lease.responsible_tenant_id == tenant.id
        assert new_lease.contract_generated is False
        assert new_lease.contract_signed is False
        assert new_lease.interfone_configured is False

    def test_transfer_assigns_tenants_to_new_lease(
        self, active_lease, new_apt, tenant, staff_user
    ):
        new_lease = transfer_lease(
            lease_id=active_lease.id,
            payload={
                "apartment_id": new_apt.id,
                "responsible_tenant_id": tenant.id,
                "tenant_ids": [tenant.id],
                "start_date": "2026-01-01",
                "validity_months": 12,
                "tag_fee": 50,
            },
            user=staff_user,
        )

        assert list(new_lease.tenants.values_list("id", flat=True)) == [tenant.id]

    def test_transfer_soft_deletes_old_lease(
        self, active_lease, new_apt, tenant, old_apt, staff_user
    ):
        transfer_lease(
            lease_id=active_lease.id,
            payload={
                "apartment_id": new_apt.id,
                "responsible_tenant_id": tenant.id,
                "tenant_ids": [tenant.id],
                "start_date": "2026-01-01",
                "validity_months": 12,
                "tag_fee": 50,
            },
            user=staff_user,
        )

        active_lease.refresh_from_db()
        assert active_lease.is_deleted is True
        old_apt.refresh_from_db()
        assert old_apt.is_rented is False

    def test_transfer_marks_new_apartment_as_rented(
        self, active_lease, new_apt, tenant, staff_user
    ):
        transfer_lease(
            lease_id=active_lease.id,
            payload={
                "apartment_id": new_apt.id,
                "responsible_tenant_id": tenant.id,
                "tenant_ids": [tenant.id],
                "start_date": "2026-01-01",
                "validity_months": 12,
                "tag_fee": 50,
            },
            user=staff_user,
        )

        new_apt.refresh_from_db()
        assert new_apt.is_rented is True

    def test_transfer_to_rented_apartment_raises(
        self, active_lease, new_apt, tenant, second_tenant, staff_user
    ):
        # Occupy new_apt first
        Lease.objects.create(
            apartment=new_apt,
            responsible_tenant=second_tenant,
            start_date="2026-01-01",
            validity_months=12,
            tag_fee=50,
        )

        with pytest.raises(ValueError, match="já está alugado"):
            transfer_lease(
                lease_id=active_lease.id,
                payload={
                    "apartment_id": new_apt.id,
                    "responsible_tenant_id": tenant.id,
                    "tenant_ids": [tenant.id],
                    "start_date": "2026-01-01",
                    "validity_months": 12,
                    "tag_fee": 50,
                },
                user=staff_user,
            )

    def test_transfer_nonexistent_lease_raises(self, new_apt, tenant, staff_user):
        with pytest.raises(Lease.DoesNotExist):
            transfer_lease(
                lease_id=99999,
                payload={
                    "apartment_id": new_apt.id,
                    "responsible_tenant_id": tenant.id,
                    "start_date": "2026-01-01",
                    "validity_months": 12,
                    "tag_fee": 50,
                },
                user=staff_user,
            )
