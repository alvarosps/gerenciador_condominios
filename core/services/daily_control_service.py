"""
Daily control service for financial module.

Provides day-by-day breakdown of expected/actual income and expenses,
monthly summaries, and mark-paid functionality.
"""

import calendar
import datetime as dt
from datetime import date
from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from core.models import (
    Expense,
    ExpenseInstallment,
    ExpenseType,
    Income,
    Lease,
    RentPayment,
)

DAYS_OF_WEEK_PT = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}


class DailyControlService:
    """Service for daily financial control — breakdown, summary, and mark-paid."""

    @staticmethod
    def get_daily_breakdown(year: int, month: int) -> list[dict[str, Any]]:
        """
        Return day-by-day breakdown of entries and exits for the given month.

        For each day, collects:
        - Entries: rent payments expected (lease.due_day), recurring income, one-time income
        - Exits: expense installments (due_date), fixed recurring expenses (recurrence_day),
                 one-time expenses (expense_date)

        Excludes offset expenses (is_offset=True).
        """
        month_start = date(year, month, 1)
        _, days_in_month = calendar.monthrange(year, month)
        next_month_start = _next_month_start(year, month)

        # Pre-fetch all data for the month
        entries_by_day = _collect_entries_by_day(year, month, month_start, next_month_start)
        exits_by_day = _collect_exits_by_day(year, month, month_start, next_month_start)

        # Build day-by-day result
        cumulative_balance = Decimal("0.00")
        days = []

        for day_num in range(1, days_in_month + 1):
            current_date = date(year, month, day_num)
            day_key = day_num

            day_entries = entries_by_day.get(day_key, [])
            day_exits = exits_by_day.get(day_key, [])

            total_entries = sum(Decimal(str(e["amount"])) for e in day_entries)
            total_exits = sum(Decimal(str(e["amount"])) for e in day_exits)
            day_balance = total_entries - total_exits
            cumulative_balance += day_balance

            days.append(
                {
                    "date": current_date.isoformat(),
                    "day_of_week": DAYS_OF_WEEK_PT[current_date.weekday()],
                    "entries": day_entries,
                    "exits": day_exits,
                    "total_entries": total_entries,
                    "total_exits": total_exits,
                    "day_balance": day_balance,
                    "cumulative_balance": cumulative_balance,
                }
            )

        return days

    @staticmethod
    def get_month_summary(year: int, month: int) -> dict[str, Any]:
        """
        Return aggregated summary for the month.

        Includes expected vs actual totals, overdue counts, and balance projections.
        """
        today = date.today()
        month_start = date(year, month, 1)
        next_month_start = _next_month_start(year, month)

        # Expected income: rent from active leases + recurring income + one-time income in month
        expected_rent = _get_expected_rent_total(year, month, month_start)
        expected_extra = _get_expected_extra_income(month_start, next_month_start)
        total_expected_income = expected_rent + expected_extra

        # Received income: actual rent payments + received income
        received_rent = _get_received_rent_total(month_start)
        received_extra = _get_received_extra_income(month_start, next_month_start)
        total_received_income = received_rent + received_extra

        # Expected expenses: installments + fixed + one-time in month
        total_expected_expenses = _get_expected_expenses_total(month_start, next_month_start)

        # Paid expenses: paid installments + paid expenses in month
        total_paid_expenses = _get_paid_expenses_total(month_start, next_month_start)

        # Overdue: unpaid items with due_date < today (only for current/past months)
        overdue_count, overdue_total = _get_overdue_totals(month_start, next_month_start, today)

        # Upcoming 7 days
        upcoming_count, upcoming_total = _get_upcoming_7_days(today)

        current_balance = total_received_income - total_paid_expenses
        projected_balance = total_expected_income - total_expected_expenses

        return {
            "total_expected_income": total_expected_income,
            "total_received_income": total_received_income,
            "total_expected_expenses": total_expected_expenses,
            "total_paid_expenses": total_paid_expenses,
            "overdue_count": overdue_count,
            "overdue_total": overdue_total,
            "upcoming_7_days_count": upcoming_count,
            "upcoming_7_days_total": upcoming_total,
            "current_balance": current_balance,
            "projected_balance": projected_balance,
        }

    @staticmethod
    def mark_item_paid(item_type: str, item_id: int, payment_date: date) -> dict[str, Any]:
        """
        Mark an item as paid.

        Supports: "installment", "expense", "income".
        Validates item exists and is not already paid.
        """
        if item_type == "installment":
            return _mark_installment_paid(item_id, payment_date)
        if item_type == "expense":
            return _mark_expense_paid(item_id, payment_date)
        if item_type == "income":
            return _mark_income_received(item_id, payment_date)

        msg = f"Tipo de item inválido: {item_type}"
        raise ValueError(msg)


# ──────────────────────────────────────────
# Private helper functions
# ──────────────────────────────────────────

MONTHS_IN_YEAR = 12


def _next_month_start(year: int, month: int) -> date:
    """Return the first day of the month following (year, month)."""
    if month == MONTHS_IN_YEAR:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def _mark_installment_paid(item_id: int, payment_date: date) -> dict[str, Any]:
    """Mark an installment as paid."""
    try:
        item = ExpenseInstallment.objects.get(pk=item_id)
    except ExpenseInstallment.DoesNotExist as err:
        msg = f"Parcela {item_id} não encontrada."
        raise ObjectDoesNotExist(msg) from err
    if item.is_paid:
        return {"status": "already_paid", "message": "Parcela já está paga."}
    item.is_paid = True
    item.paid_date = payment_date
    item.save(update_fields=["is_paid", "paid_date", "updated_at"])
    return {"status": "ok", "message": f"Parcela {item_id} marcada como paga."}


def _mark_expense_paid(item_id: int, payment_date: date) -> dict[str, Any]:
    """Mark an expense as paid."""
    try:
        item = Expense.objects.get(pk=item_id)
    except Expense.DoesNotExist as err:
        msg = f"Despesa {item_id} não encontrada."
        raise ObjectDoesNotExist(msg) from err
    if item.is_paid:
        return {"status": "already_paid", "message": "Despesa já está paga."}
    item.is_paid = True
    item.paid_date = payment_date
    item.save(update_fields=["is_paid", "paid_date", "updated_at"])
    return {"status": "ok", "message": f"Despesa {item_id} marcada como paga."}


def _mark_income_received(item_id: int, payment_date: date) -> dict[str, Any]:
    """Mark an income as received."""
    try:
        item = Income.objects.get(pk=item_id)
    except Income.DoesNotExist as err:
        msg = f"Receita {item_id} não encontrada."
        raise ObjectDoesNotExist(msg) from err
    if item.is_received:
        return {"status": "already_paid", "message": "Receita já está recebida."}
    item.is_received = True
    item.received_date = payment_date
    item.save(update_fields=["is_received", "received_date", "updated_at"])
    return {"status": "ok", "message": f"Receita {item_id} marcada como recebida."}


def _collect_entries_by_day(
    year: int,
    month: int,
    month_start: date,
    next_month_start: date,
) -> dict[int, list[dict[str, Any]]]:
    """Collect all income entries grouped by day of month."""
    entries: dict[int, list[dict[str, Any]]] = {}

    # 1. Rent payments expected (from active leases with due_day in this month)
    leases = (
        Lease.objects.filter(apartment__is_rented=True)
        .exclude(apartment__owner__isnull=False)
        .exclude(prepaid_until__gte=month_start)
        .exclude(is_salary_offset=True)
        .select_related("apartment", "apartment__building", "responsible_tenant")
    )

    rent_payments = {
        rp.lease_id: rp
        for rp in RentPayment.objects.filter(reference_month=month_start).select_related("lease")
    }

    _, days_in_month = calendar.monthrange(year, month)

    for lease in leases:
        due = min(lease.responsible_tenant.due_day, days_in_month)
        payment = rent_payments.get(lease.id)
        entry = {
            "type": "rent",
            "description": f"Aluguel Apto {lease.apartment.number}/{lease.apartment.building.street_number}",
            "amount": float(lease.apartment.rental_value),
            "expected": True,
            "paid": payment is not None,
        }
        if payment:
            entry["payment_date"] = payment.payment_date.isoformat()
        entries.setdefault(due, []).append(entry)

    # 2. Recurring income (expected_monthly_amount, using income_date.day as recurrence day)
    recurring_incomes = Income.objects.filter(
        is_recurring=True,
        expected_monthly_amount__isnull=False,
    )
    for inc in recurring_incomes:
        recurrence_day = min(inc.income_date.day, days_in_month)
        # Check if received this month
        received_this_month = Income.objects.filter(
            pk=inc.pk,
            is_received=True,
            received_date__gte=month_start,
            received_date__lt=next_month_start,
        ).exists()
        entry = {
            "type": "income",
            "id": inc.id,
            "description": inc.description,
            "amount": float(inc.expected_monthly_amount),
            "expected": True,
            "paid": inc.is_received or received_this_month,
        }
        if inc.is_received and inc.received_date:
            entry["payment_date"] = inc.received_date.isoformat()
        entries.setdefault(recurrence_day, []).append(entry)

    # 3. One-time income in this month
    one_time_incomes = Income.objects.filter(
        is_recurring=False,
        income_date__gte=month_start,
        income_date__lt=next_month_start,
    )
    for inc in one_time_incomes:
        entry = {
            "type": "income",
            "id": inc.id,
            "description": inc.description,
            "amount": float(inc.amount),
            "expected": True,
            "paid": inc.is_received,
        }
        if inc.is_received and inc.received_date:
            entry["payment_date"] = inc.received_date.isoformat()
        entries.setdefault(inc.income_date.day, []).append(entry)

    return entries


def _collect_exits_by_day(
    year: int,
    month: int,
    month_start: date,
    next_month_start: date,
) -> dict[int, list[dict[str, Any]]]:
    """Collect all expense exits grouped by day of month."""
    exits: dict[int, list[dict[str, Any]]] = {}
    _, days_in_month = calendar.monthrange(year, month)

    _collect_installment_exits(exits, month_start, next_month_start)
    _collect_fixed_expense_exits(exits, month_start, days_in_month)
    _collect_dated_expense_exits(exits, month_start, next_month_start)

    return exits


def _collect_installment_exits(
    exits: dict[int, list[dict[str, Any]]], month_start: date, next_month_start: date
) -> None:
    """Add installment exits to the exits dict."""
    installments = ExpenseInstallment.objects.filter(
        due_date__gte=month_start,
        due_date__lt=next_month_start,
        expense__is_offset=False,
    ).select_related("expense", "expense__person", "expense__credit_card")

    for inst in installments:
        day = inst.due_date.day
        exit_item: dict[str, Any] = {
            "type": "installment",
            "id": inst.id,
            "description": f"{inst.expense.description} {inst.installment_number}/{inst.total_installments}",
            "amount": float(inst.amount),
            "due": True,
            "paid": inst.is_paid,
        }
        if inst.expense.person:
            exit_item["person"] = inst.expense.person.name
        if inst.expense.credit_card:
            exit_item["card"] = inst.expense.credit_card.nickname
        if inst.is_paid and inst.paid_date:
            exit_item["payment_date"] = inst.paid_date.isoformat()
        exits.setdefault(day, []).append(exit_item)


def _collect_fixed_expense_exits(
    exits: dict[int, list[dict[str, Any]]], month_start: date, days_in_month: int
) -> None:
    """Add fixed recurring expense exits to the exits dict."""
    fixed_expenses = (
        Expense.objects.filter(
            expense_type=ExpenseType.FIXED_EXPENSE,
            is_recurring=True,
            is_offset=False,
            expected_monthly_amount__isnull=False,
        )
        .exclude(end_date__lt=month_start)
        .select_related("person")
    )

    for exp in fixed_expenses:
        day = min(exp.recurrence_day or 1, days_in_month)
        exit_item: dict[str, Any] = {
            "type": "expense",
            "id": exp.id,
            "description": exp.description,
            "amount": float(exp.expected_monthly_amount),
            "due": True,
            "paid": exp.is_paid,
        }
        if exp.person:
            exit_item["person"] = exp.person.name
        if exp.is_paid and exp.paid_date:
            exit_item["payment_date"] = exp.paid_date.isoformat()
        exits.setdefault(day, []).append(exit_item)


def _collect_dated_expense_exits(
    exits: dict[int, list[dict[str, Any]]], month_start: date, next_month_start: date
) -> None:
    """Add one-time and utility bill exits to the exits dict."""
    # One-time expenses
    one_time_expenses = Expense.objects.filter(
        expense_type=ExpenseType.ONE_TIME_EXPENSE,
        is_offset=False,
        expense_date__gte=month_start,
        expense_date__lt=next_month_start,
    )
    for exp in one_time_expenses:
        exit_item: dict[str, Any] = {
            "type": "expense",
            "id": exp.id,
            "description": exp.description,
            "amount": float(exp.total_amount),
            "due": True,
            "paid": exp.is_paid,
        }
        if exp.is_paid and exp.paid_date:
            exit_item["payment_date"] = exp.paid_date.isoformat()
        exits.setdefault(exp.expense_date.day, []).append(exit_item)

    # Utility bills
    utility_expenses = Expense.objects.filter(
        expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
        is_offset=False,
        expense_date__gte=month_start,
        expense_date__lt=next_month_start,
    ).select_related("building")
    for exp in utility_expenses:
        exit_item = {
            "type": "expense",
            "id": exp.id,
            "description": exp.description,
            "amount": float(exp.total_amount),
            "due": True,
            "paid": exp.is_paid,
        }
        if exp.building:
            exit_item["building"] = exp.building.street_number
        if exp.is_paid and exp.paid_date:
            exit_item["payment_date"] = exp.paid_date.isoformat()
        exits.setdefault(exp.expense_date.day, []).append(exit_item)


def _get_expected_rent_total(year: int, month: int, month_start: date) -> Decimal:
    """Total expected rent income from active leases."""
    leases = (
        Lease.objects.filter(apartment__is_rented=True)
        .exclude(apartment__owner__isnull=False)
        .exclude(prepaid_until__gte=month_start)
        .exclude(is_salary_offset=True)
    )
    total = Decimal("0.00")
    for lease in leases:
        total += lease.apartment.rental_value
    return total


def _get_expected_extra_income(month_start: date, next_month_start: date) -> Decimal:
    """Total expected extra income (recurring + one-time in month)."""
    total = Decimal("0.00")
    # Recurring
    recurring = Income.objects.filter(
        is_recurring=True,
        expected_monthly_amount__isnull=False,
    )
    for inc in recurring:
        total += inc.expected_monthly_amount or Decimal("0.00")
    # One-time in month
    one_time = Income.objects.filter(
        is_recurring=False,
        income_date__gte=month_start,
        income_date__lt=next_month_start,
    )
    for inc in one_time:
        total += inc.amount
    return total


def _get_received_rent_total(month_start: date) -> Decimal:
    """Total received rent payments for the month."""
    payments = RentPayment.objects.filter(reference_month=month_start)
    total = Decimal("0.00")
    for rp in payments:
        total += rp.amount_paid
    return total


def _get_received_extra_income(month_start: date, next_month_start: date) -> Decimal:
    """Total received extra income for the month."""
    total = Decimal("0.00")
    received = Income.objects.filter(
        is_received=True,
        received_date__gte=month_start,
        received_date__lt=next_month_start,
    )
    for inc in received:
        total += inc.amount
    return total


def _get_expected_expenses_total(month_start: date, next_month_start: date) -> Decimal:
    """Total expected expenses for the month (installments + fixed + one-time + utility)."""
    total = Decimal("0.00")

    # Installments (exclude offsets)
    installments = ExpenseInstallment.objects.filter(
        due_date__gte=month_start,
        due_date__lt=next_month_start,
        expense__is_offset=False,
    )
    for inst in installments:
        total += inst.amount

    # Fixed recurring (exclude offsets, respect end_date)
    fixed = Expense.objects.filter(
        expense_type=ExpenseType.FIXED_EXPENSE,
        is_recurring=True,
        is_offset=False,
        expected_monthly_amount__isnull=False,
    ).exclude(end_date__lt=month_start)
    for exp in fixed:
        total += exp.expected_monthly_amount or Decimal("0.00")

    # One-time expenses
    one_time = Expense.objects.filter(
        expense_type=ExpenseType.ONE_TIME_EXPENSE,
        is_offset=False,
        expense_date__gte=month_start,
        expense_date__lt=next_month_start,
    )
    for exp in one_time:
        total += exp.total_amount

    # Utility bills
    utilities = Expense.objects.filter(
        expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
        is_offset=False,
        expense_date__gte=month_start,
        expense_date__lt=next_month_start,
    )
    for exp in utilities:
        total += exp.total_amount

    return total


def _get_paid_expenses_total(month_start: date, next_month_start: date) -> Decimal:
    """Total paid expenses for the month."""
    total = Decimal("0.00")

    # Paid installments
    paid_installments = ExpenseInstallment.objects.filter(
        due_date__gte=month_start,
        due_date__lt=next_month_start,
        is_paid=True,
        expense__is_offset=False,
    )
    for inst in paid_installments:
        total += inst.amount

    # Paid fixed recurring
    # For fixed expenses, we check is_paid flag
    paid_fixed = Expense.objects.filter(
        expense_type=ExpenseType.FIXED_EXPENSE,
        is_recurring=True,
        is_offset=False,
        is_paid=True,
        paid_date__gte=month_start,
        paid_date__lt=next_month_start,
    )
    for exp in paid_fixed:
        total += exp.expected_monthly_amount or exp.total_amount

    # Paid one-time expenses
    paid_one_time = Expense.objects.filter(
        expense_type=ExpenseType.ONE_TIME_EXPENSE,
        is_offset=False,
        is_paid=True,
        expense_date__gte=month_start,
        expense_date__lt=next_month_start,
    )
    for exp in paid_one_time:
        total += exp.total_amount

    # Paid utility bills
    paid_utilities = Expense.objects.filter(
        expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
        is_offset=False,
        is_paid=True,
        expense_date__gte=month_start,
        expense_date__lt=next_month_start,
    )
    for exp in paid_utilities:
        total += exp.total_amount

    return total


def _get_overdue_totals(
    month_start: date, next_month_start: date, today: date
) -> tuple[int, Decimal]:
    """Count and sum overdue items (unpaid with due_date before today)."""
    count = 0
    total = Decimal("0.00")

    # Overdue installments
    overdue_installments = ExpenseInstallment.objects.filter(
        due_date__gte=month_start,
        due_date__lt=min(next_month_start, today),
        is_paid=False,
        expense__is_offset=False,
    )
    for inst in overdue_installments:
        count += 1
        total += inst.amount

    # Overdue one-time/utility expenses
    overdue_expenses = Expense.objects.filter(
        expense_type__in=[
            ExpenseType.ONE_TIME_EXPENSE,
            ExpenseType.WATER_BILL,
            ExpenseType.ELECTRICITY_BILL,
        ],
        is_offset=False,
        is_paid=False,
        expense_date__gte=month_start,
        expense_date__lt=min(next_month_start, today),
    )
    for exp in overdue_expenses:
        count += 1
        total += exp.total_amount

    return count, total


def _get_upcoming_7_days(today: date) -> tuple[int, Decimal]:
    """Count and sum items due in the next 7 days."""

    end_date = today + dt.timedelta(days=7)
    count = 0
    total = Decimal("0.00")

    # Upcoming installments
    upcoming_installments = ExpenseInstallment.objects.filter(
        due_date__gte=today,
        due_date__lt=end_date,
        is_paid=False,
        expense__is_offset=False,
    )
    for inst in upcoming_installments:
        count += 1
        total += inst.amount

    return count, total
