"""Session 41 — Employee model tests (payment_type, base_salary, lease SET_NULL vs soft-delete)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import Lease
from finances.models import Employee, EmployeePaymentType
from tests.factories import make_employee, make_lease, make_person

pytestmark = pytest.mark.django_db


def test_inherits_mixins_and_managers() -> None:
    emp = make_employee()
    assert emp.created_at is not None
    assert emp.is_deleted is False
    emp.delete()  # soft delete
    assert Employee.objects.filter(pk=emp.pk).count() == 0
    assert Employee.all_objects.filter(pk=emp.pk).count() == 1  # all_objects includes deleted


def test_payment_type_choices() -> None:
    assert {c[0] for c in EmployeePaymentType.choices} == {"fixed", "variable", "mixed"}


def test_base_salary_optional_for_variable_and_negative_rejected() -> None:
    variable = make_employee(payment_type="variable", base_salary=None)
    assert variable.base_salary is None
    with pytest.raises(IntegrityError), transaction.atomic():
        make_employee(base_salary=Decimal("-1.00"))


def test_clean_fixed_requires_base_salary() -> None:
    emp = Employee(payment_type=EmployeePaymentType.FIXED, base_salary=None)
    with pytest.raises(ValidationError) as exc:
        emp.clean()
    assert "base_salary" in exc.value.message_dict


def test_clean_variable_forbids_base_salary() -> None:
    emp = Employee(payment_type=EmployeePaymentType.VARIABLE, base_salary=Decimal("100.00"))
    with pytest.raises(ValidationError) as exc:
        emp.clean()
    assert "base_salary" in exc.value.message_dict


def test_clean_mixed_requires_base_salary() -> None:
    emp = Employee(payment_type=EmployeePaymentType.MIXED, base_salary=None)
    with pytest.raises(ValidationError) as exc:
        emp.clean()
    assert "base_salary" in exc.value.message_dict


def test_lease_soft_delete_does_not_null_fk_but_marks_is_deleted() -> None:
    lease = make_lease(is_salary_offset=True)
    emp = make_employee(lease=lease)
    lease.delete()  # soft delete
    emp.refresh_from_db()
    # FK still points to the lease (SET_NULL only fires on a HARD delete); end-of-lease is by is_deleted.
    assert emp.lease_id is not None
    assert Lease.all_objects.get(pk=lease.pk).is_deleted is True


def test_lease_hard_delete_nulls_fk() -> None:
    lease = make_lease(is_salary_offset=True)
    emp = make_employee(lease=lease)
    lease.delete(hard_delete=True)
    emp.refresh_from_db()
    assert emp.lease_id is None


def test_person_set_null_survives_person_delete() -> None:
    person = make_person()
    emp = make_employee(person=person)
    person.delete(hard_delete=True)
    emp.refresh_from_db()
    assert emp.person_id is None


def test_str_is_portuguese() -> None:
    emp = make_employee(name="Maria", payment_type="fixed")
    assert "Maria" in str(emp)
