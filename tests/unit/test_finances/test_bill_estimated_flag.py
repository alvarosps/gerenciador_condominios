"""Session 65 — Bill.amount_is_estimated: service-only transitions (generate/edit/pay/reverse).

True is set exactly once, via BillGenerationService._ensure_account_bill's get_or_create
defaults, when a recurring account Bill is freshly created (including the host Bill created
by the embedded-installment path — same function, no extra code). Every other generation path
(standalone installment, payroll, create_with_lines) has a REAL amount and stays at the model
default (False). False is set by update_with_lines and pay (total/partial; bulk_pay covers it
by delegation) — both inside their existing transaction, once the real value is known. unpay
does NOT re-mark the flag (design §3.3 — the real value stays known after reversing a payment).
update_header never touches the flag (it is outside _EDITABLE_HEADER_FIELDS).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from finances.models import Bill
from finances.services.bill_generation_service import BillGenerationService
from finances.services.bill_payment_service import BillPaymentService
from finances.services.bill_service import BillDraft, BillService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condominium,
    make_employee,
    make_installment,
    make_installment_plan,
)

pytestmark = pytest.mark.django_db


class TestEstimatedFlagOnGeneration:
    def test_generated_recurring_bill_is_estimated(self) -> None:
        make_billing_account(default_due_day=10, expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        assert bill.amount_is_estimated is True

    def test_generated_bill_without_expected_amount_is_estimated(self) -> None:
        """Conta com expected_amount=0 gera bill SEM linha (total 0), ainda 'aguardando fatura'."""
        make_billing_account(expected_amount=Decimal("0.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        assert bill.amount_is_estimated is True
        assert bill.line_items.count() == 0

    def test_embedded_path_creates_estimated_host_bill(self) -> None:
        account = make_billing_account(expected_amount=Decimal("600.00"))
        plan = make_installment_plan(
            condominium=account.condominium,
            embedded=True,
            billing_account=account,
            installment_count=1,
        )
        make_installment(plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00"))
        BillGenerationService.ensure_month_bills(2026, 6)
        bill = Bill.objects.get(billing_account=account, competence_month=date(2026, 6, 1))
        assert bill.amount_is_estimated is True

    def test_regeneration_does_not_remark_flag(self) -> None:
        account = make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        bill.amount_is_estimated = False
        bill.save(update_fields=["amount_is_estimated"])

        BillGenerationService.ensure_month_bills(2026, 6)  # idempotent re-run

        bill.refresh_from_db()
        assert bill.amount_is_estimated is False
        assert Bill.all_objects.filter(billing_account=account).count() == 1

    def test_standalone_installment_bill_not_estimated(self) -> None:
        plan = make_installment_plan(embedded=False, installment_count=1)
        make_installment(plan=plan, number=1, due_date=date(2026, 6, 10), amount=Decimal("400.00"))
        BillGenerationService.ensure_month_bills(2026, 6)
        bill = Bill.objects.get(installment__plan=plan)
        assert bill.amount_is_estimated is False

    def test_payroll_bill_not_estimated(self) -> None:
        emp = make_employee(payment_type="fixed", base_salary=Decimal("2000.00"))
        BillGenerationService.ensure_month_bills(2026, 6)
        bill = Bill.objects.get(employee=emp, competence_month=date(2026, 6, 1))
        assert bill.amount_is_estimated is False


class TestEstimatedFlagTransitions:
    def test_create_with_lines_defaults_to_not_estimated(self) -> None:
        cond = make_condominium()
        draft = BillDraft(
            condominium=cond,
            competence_month=date(2026, 6, 1),
            due_date=date(2026, 6, 10),
            description="Conta avulsa",
            behavior="one_time",
        )
        bill = BillService.create_with_lines(
            draft, [{"description": "X", "amount": Decimal("50.00")}]
        )
        assert bill.amount_is_estimated is False

    def test_update_with_lines_clears_flag(self) -> None:
        account = make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        assert bill.amount_is_estimated is True

        BillService.update_with_lines(
            bill, [{"description": account.name, "amount": Decimal("650.00")}]
        )

        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

    def test_update_with_lines_keeps_false(self) -> None:
        bill = make_bill(competence_month=date(2026, 6, 1), amount_is_estimated=False)
        make_bill_line_item(bill=bill, amount=Decimal("100.00"))

        BillService.update_with_lines(bill, [{"description": "Nova", "amount": Decimal("120.00")}])

        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

    def test_pay_full_clears_flag(self) -> None:
        make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        assert bill.amount_is_estimated is True

        BillPaymentService.pay(bill, date(2026, 6, 5))

        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

    def test_pay_partial_clears_flag(self) -> None:
        make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]

        BillPaymentService.pay(bill, date(2026, 6, 5), amount=Decimal("200.00"))

        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

    def test_unpay_does_not_remark_flag(self) -> None:
        make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        payment = BillPaymentService.pay(bill, date(2026, 6, 5))
        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

        BillPaymentService.unpay(payment)

        bill.refresh_from_db()
        assert bill.amount_is_estimated is False

    def test_update_header_does_not_touch_flag(self) -> None:
        make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        assert bill.amount_is_estimated is True

        BillService.update_header(bill, {"description": "Água — corrigida"})

        bill.refresh_from_db()
        assert bill.amount_is_estimated is True
        assert bill.description == "Água — corrigida"

    def test_failed_pay_keeps_flag(self) -> None:
        make_billing_account(expected_amount=Decimal("600.00"))
        bill = BillGenerationService.ensure_month_bills(2026, 6)[0]
        assert bill.amount_is_estimated is True

        with pytest.raises(ValidationError):
            BillPaymentService.pay(bill, date(2026, 6, 5), amount=Decimal("10000.00"))

        bill.refresh_from_db()
        assert bill.amount_is_estimated is True
