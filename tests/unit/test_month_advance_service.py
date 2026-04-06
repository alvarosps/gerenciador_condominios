"""Unit tests for MonthAdvanceService.

Tests snapshot creation, validation, rollback, and next-month preparation
using a real test database. No internal services are mocked.
"""

from datetime import date
from decimal import Decimal

import pytest

from core.models import (
    Apartment,
    Building,
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    FinancialSettings,
    Lease,
    MonthSnapshot,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
    RentPayment,
    Tenant,
)
from core.services.month_advance_service import MonthAdvanceService

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    return MonthAdvanceService()


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=9900,
        name="Edifício MonthAdvance Test",
        address="Rua Test, 9900",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Inquilino MonthAdvance",
        cpf_cnpj="52998224725",
        is_company=False,
        phone="11977770099",
        marital_status="Solteiro(a)",
        profession="Analista",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def active_lease(apartment, tenant, admin_user):
    """Active lease that triggers apartment.is_rented=True via signal."""
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=24,
        tag_fee=Decimal("80.00"),
        rental_value=Decimal("1500.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def rent_payment(active_lease, admin_user):
    """RentPayment for 2026-01 — satisfies unpaid_rent check."""
    return RentPayment.objects.create(
        lease=active_lease,
        reference_month=date(2026, 1, 1),
        amount_paid=Decimal("1500.00"),
        payment_date=date(2026, 1, 15),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee(admin_user):
    return Person.objects.create(
        name="Funcionário Test",
        relationship="Funcionário",
        phone="11977770001",
        is_employee=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_payment_jan(employee, admin_user):
    return EmployeePayment.objects.create(
        person=employee,
        reference_month=date(2026, 1, 1),
        base_salary=Decimal("2000.00"),
        variable_amount=Decimal("0.00"),
        rent_offset=Decimal("0.00"),
        cleaning_count=0,
        is_paid=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def financial_settings(admin_user):
    return FinancialSettings.objects.create(
        initial_balance=Decimal("1000.00"),
        initial_balance_date=date(2026, 1, 1),
        updated_by=admin_user,
    )


@pytest.fixture
def water_bill_jan(admin_user):
    return Expense.objects.create(
        description="Conta de Água Jan/2026",
        expense_type="water_bill",
        total_amount=Decimal("200.00"),
        expense_date=date(2026, 1, 15),
        is_paid=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def electricity_bill_jan(admin_user):
    return Expense.objects.create(
        description="Conta de Luz Jan/2026",
        expense_type="electricity_bill",
        total_amount=Decimal("300.00"),
        expense_date=date(2026, 1, 20),
        is_paid=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def clean_month_jan(
    rent_payment,
    employee_payment_jan,
    water_bill_jan,
    electricity_bill_jan,
    financial_settings,
):
    """Fixture that satisfies all validation checks for 2026-01."""
    return {
        "year": 2026,
        "month": 1,
    }


# ---------------------------------------------------------------------------
# TestMonthAdvanceService
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMonthAdvanceService:
    def test_advance_creates_finalized_snapshot(self, service, active_lease, clean_month_jan):
        result = service.advance_month(2026, 1, force=True)

        assert result["success"] is True
        snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))
        assert snapshot.is_finalized is True
        assert snapshot.finalized_at is not None

    def test_advance_idempotent_raises_on_second_call(self, service, active_lease, clean_month_jan):
        service.advance_month(2026, 1, force=True)

        with pytest.raises(ValueError, match="já foi finalizado"):
            service.advance_month(2026, 1, force=True)

    def test_advance_requires_force_when_warnings_exist(self, service, active_lease):
        # No rent payment, no employee payments — validation will have warnings
        with pytest.raises(ValueError, match="force=True"):
            service.advance_month(2026, 1, force=False)

    def test_advance_with_force_includes_warnings_in_snapshot(self, service, active_lease):
        # active_lease has unpaid rent → validation warning
        result = service.advance_month(2026, 1, force=True)

        assert len(result["warnings"]) > 0
        snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))
        assert len(snapshot.detailed_breakdown["validation_warnings"]) > 0

    def test_advance_creates_employee_payments_for_next_month(
        self, service, active_lease, clean_month_jan, employee, employee_payment_jan
    ):
        result = service.advance_month(2026, 1, force=True)

        # Should have created EmployeePayment for 2026-02
        next_month_payment = EmployeePayment.objects.filter(
            person=employee,
            reference_month=date(2026, 2, 1),
        ).first()
        assert next_month_payment is not None
        assert next_month_payment.is_paid is False
        assert next_month_payment.base_salary == Decimal("2000.00")
        assert result["next_month_preview"]["auto_created"]["employee_payments_created"] == 1

    def test_advance_carries_forward_payment_schedules(
        self, service, active_lease, clean_month_jan, admin_user
    ):
        person = Person.objects.create(
            name="Pessoa Schedule Test",
            relationship="Proprietário",
            phone="11900000001",
            created_by=admin_user,
            updated_by=admin_user,
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 1, 1),
            due_day=15,
            amount=Decimal("500.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        result = service.advance_month(2026, 1, force=True)

        next_schedule = PersonPaymentSchedule.objects.filter(
            person=person,
            reference_month=date(2026, 2, 1),
        ).first()
        assert next_schedule is not None
        assert next_schedule.amount == Decimal("500.00")
        assert next_schedule.due_day == 15
        assert result["next_month_preview"]["auto_created"]["payment_schedules_created"] >= 1

    def test_advance_calculates_cumulative_ending_balance(
        self, service, active_lease, financial_settings, clean_month_jan
    ):
        result = service.advance_month(2026, 1, force=True)

        snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))
        expected_cumulative = financial_settings.initial_balance + snapshot.net_balance
        assert snapshot.cumulative_ending_balance == expected_cumulative
        assert result["summary"]["cumulative_ending_balance"] == float(expected_cumulative)

    def test_advance_cumulative_balance_chains_from_previous_snapshot(
        self, service, active_lease, financial_settings, clean_month_jan, admin_user
    ):
        # Advance January
        service.advance_month(2026, 1, force=True)
        jan_snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))

        # Add rent payment for February so it's clean
        RentPayment.objects.create(
            lease=active_lease,
            reference_month=date(2026, 2, 1),
            amount_paid=Decimal("1500.00"),
            payment_date=date(2026, 2, 15),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Advance February
        service.advance_month(2026, 2, force=True)
        feb_snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 2, 1))

        expected = jan_snapshot.cumulative_ending_balance + feb_snapshot.net_balance
        assert feb_snapshot.cumulative_ending_balance == expected

    def test_rollback_deletes_snapshot(self, service, active_lease, clean_month_jan):
        service.advance_month(2026, 1, force=True)
        assert MonthSnapshot.objects.filter(reference_month=date(2026, 1, 1)).exists()

        result = service.rollback_month(2026, 1, confirm=True)

        assert result["success"] is True
        assert not MonthSnapshot.objects.filter(reference_month=date(2026, 1, 1)).exists()

    def test_rollback_requires_confirm(self, service, active_lease, clean_month_jan):
        service.advance_month(2026, 1, force=True)

        with pytest.raises(ValueError, match="confirm=True"):
            service.rollback_month(2026, 1, confirm=False)

    def test_rollback_only_last_month(self, service, active_lease, clean_month_jan, admin_user):
        service.advance_month(2026, 1, force=True)

        # Add rent payment for February
        RentPayment.objects.create(
            lease=active_lease,
            reference_month=date(2026, 2, 1),
            amount_paid=Decimal("1500.00"),
            payment_date=date(2026, 2, 10),
            created_by=admin_user,
            updated_by=admin_user,
        )
        service.advance_month(2026, 2, force=True)

        # Cannot rollback January when February is the latest
        with pytest.raises(ValueError, match="último mês"):
            service.rollback_month(2026, 1, confirm=True)

    def test_rollback_cleans_up_auto_created_records(
        self, service, active_lease, clean_month_jan, employee, employee_payment_jan, admin_user
    ):
        person = Person.objects.create(
            name="Pessoa Rollback Test",
            relationship="Proprietário",
            phone="11900000002",
            created_by=admin_user,
            updated_by=admin_user,
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 1, 1),
            due_day=10,
            amount=Decimal("300.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        service.advance_month(2026, 1, force=True)

        # Verify auto-created records exist for February
        assert EmployeePayment.objects.filter(
            person=employee, reference_month=date(2026, 2, 1)
        ).exists()
        assert PersonPaymentSchedule.objects.filter(
            person=person, reference_month=date(2026, 2, 1)
        ).exists()

        result = service.rollback_month(2026, 1, confirm=True)

        # Auto-created records should be cleaned up
        assert not EmployeePayment.objects.filter(
            person=employee, reference_month=date(2026, 2, 1)
        ).exists()
        assert not PersonPaymentSchedule.objects.filter(
            person=person, reference_month=date(2026, 2, 1)
        ).exists()
        assert result["details"]["employee_payments_deleted"] >= 1
        assert result["details"]["schedules_deleted"] >= 1

    def test_status_returns_validation_and_finalized_flag(self, service, active_lease):
        status_before = service.get_status(2026, 1)

        assert status_before["year"] == 2026
        assert status_before["month"] == 1
        assert status_before["is_finalized"] is False
        assert status_before["snapshot_id"] is None
        assert "validation" in status_before
        validation = status_before["validation"]
        assert "unpaid_rent" in validation
        assert "unpaid_installments" in validation
        assert "unpaid_employees" in validation
        assert "missing_utility_bills" in validation
        assert "unpaid_person_schedules" in validation

    def test_status_finalized_after_advance(self, service, active_lease, clean_month_jan):
        service.advance_month(2026, 1, force=True)
        status_after = service.get_status(2026, 1)

        assert status_after["is_finalized"] is True
        assert status_after["snapshot_id"] is not None

    def test_chronological_order_enforced(self, service, active_lease, clean_month_jan):
        # Advance January first
        service.advance_month(2026, 1, force=True)

        # Trying to advance March without February should fail
        with pytest.raises(ValueError, match="02/2026"):
            service.advance_month(2026, 3, force=True)

    def test_first_month_does_not_require_predecessor(self, service):
        # No prior snapshots → first advance should not require a predecessor
        result = service.advance_month(2026, 1, force=True)

        assert result["success"] is True

    def test_snapshot_contains_detailed_breakdown(self, service, active_lease, clean_month_jan):
        service.advance_month(2026, 1, force=True)

        snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))
        breakdown = snapshot.detailed_breakdown
        expected_keys = {
            "rent_details",
            "extra_income_details",
            "card_installments",
            "loan_installments",
            "utility_bills",
            "employee_salaries",
            "fixed_expenses",
            "one_time_expenses",
            "validation_warnings",
            "person_payments",
        }
        assert expected_keys.issubset(breakdown.keys())

    def test_advance_returns_next_month_preview(self, service, active_lease, clean_month_jan):
        result = service.advance_month(2026, 1, force=True)

        preview = result["next_month_preview"]
        assert preview["year"] == 2026
        assert preview["month"] == 2
        assert "upcoming_installments_count" in preview
        assert "expected_rent_count" in preview
        assert "reminders" in preview

    def test_validation_detects_unpaid_rent(self, service, active_lease):
        status_data = service.get_status(2026, 1)

        unpaid = status_data["validation"]["unpaid_rent"]
        assert len(unpaid) >= 1
        assert unpaid[0]["lease_id"] == active_lease.pk

    def test_validation_detects_missing_utility_bills(self, service):
        status_data = service.get_status(2026, 1)

        missing = status_data["validation"]["missing_utility_bills"]
        types = [b["type"] for b in missing]
        assert "water_bill" in types
        assert "electricity_bill" in types

    def test_validation_detects_unpaid_employee(self, service, employee):
        status_data = service.get_status(2026, 1)

        unpaid_employees = status_data["validation"]["unpaid_employees"]
        employee_ids = [e["person_id"] for e in unpaid_employees]
        assert employee.pk in employee_ids

    def test_validation_detects_unpaid_person_schedule(self, service, admin_user):
        person = Person.objects.create(
            name="Pessoa Schedule Validation",
            relationship="Proprietário",
            phone="11900000003",
            created_by=admin_user,
            updated_by=admin_user,
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 1, 1),
            due_day=10,
            amount=Decimal("400.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        status_data = service.get_status(2026, 1)

        unpaid_schedules = status_data["validation"]["unpaid_person_schedules"]
        person_ids = [s["person_id"] for s in unpaid_schedules]
        assert person.pk in person_ids

    def test_validation_person_schedule_satisfied_by_payment(self, service, admin_user):
        person = Person.objects.create(
            name="Pessoa Schedule Paid",
            relationship="Proprietário",
            phone="11900000004",
            created_by=admin_user,
            updated_by=admin_user,
        )
        PersonPaymentSchedule.objects.create(
            person=person,
            reference_month=date(2026, 1, 1),
            due_day=10,
            amount=Decimal("400.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )
        PersonPayment.objects.create(
            person=person,
            reference_month=date(2026, 1, 1),
            amount=Decimal("400.00"),
            payment_date=date(2026, 1, 10),
            created_by=admin_user,
            updated_by=admin_user,
        )

        status_data = service.get_status(2026, 1)

        unpaid_schedules = status_data["validation"]["unpaid_person_schedules"]
        person_ids = [s["person_id"] for s in unpaid_schedules]
        assert person.pk not in person_ids

    def test_validation_unpaid_installment_detected(self, service, admin_user):
        expense = Expense.objects.create(
            description="Parcela Test Jan",
            expense_type="installment_expense",
            total_amount=Decimal("600.00"),
            expense_date=date(2026, 1, 1),
            is_installment=True,
            total_installments=3,
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=3,
            amount=Decimal("200.00"),
            due_date=date(2026, 1, 15),
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )

        status_data = service.get_status(2026, 1)

        unpaid_installments = status_data["validation"]["unpaid_installments"]
        assert len(unpaid_installments) >= 1
        assert unpaid_installments[0]["description"] == "Parcela Test Jan"

    def test_get_next_month_preview_returns_expected_structure(self, service):
        result = service.get_next_month_preview(2026, 1)

        assert result["year"] == 2026
        assert result["month"] == 2
        assert "upcoming_installments_count" in result
        assert "expected_rent_count" in result
        assert "reminders" in result
        assert isinstance(result["reminders"], list)

    def test_december_advances_to_january_next_year(self, service, active_lease, admin_user):
        # Need to close all months Jan-Nov before Dec can be advanced without gaps.
        # Easiest: just force-advance December without prior months (first advance).
        # But chronological check requires no gaps — so delete any prior state.
        assert not MonthSnapshot.objects.filter(is_finalized=True).exists()

        result = service.advance_month(2026, 12, force=True)

        assert result["success"] is True
        preview = result["next_month_preview"]
        assert preview["year"] == 2027
        assert preview["month"] == 1
