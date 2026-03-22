"""Financial dashboard service for aggregated financial metrics.

Provides overview, debt breakdowns, upcoming/overdue installments,
and expense category analysis for the financial dashboard widgets.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from core.models import (
    CreditCard,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    Person,
)

from .cash_flow_service import MONTHS_IN_YEAR, CashFlowService

MAX_BREAK_EVEN_MONTHS = 60


def _next_month_start(year: int, month: int) -> date:
    """Return the first day of the month following (year, month)."""
    if month == MONTHS_IN_YEAR:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


class FinancialDashboardService:
    """Aggregated financial metrics for dashboard widgets."""

    @staticmethod
    def get_overview() -> dict[str, Any]:
        """
        Return financial overview with current month balance, debts,
        monthly obligations/income, and months until break-even.
        """
        today = date.today()
        year, month = today.year, today.month

        # Current month via CashFlowService
        cash_flow = CashFlowService.get_monthly_cash_flow(year, month)
        current_month_income = cash_flow["income"]["total"]
        current_month_expenses = cash_flow["expenses"]["total"]
        current_month_balance = cash_flow["balance"]

        # Total debt: all unpaid installments (excluding offsets — those are discounts, not real debt)
        total_debt = ExpenseInstallment.objects.filter(
            is_paid=False,
            expense__is_offset=False,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        # Monthly obligations estimate: installments due this month (unpaid, excluding offsets)
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        total_monthly_obligations = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            is_paid=False,
            expense__is_offset=False,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        total_monthly_income = current_month_income

        # Months until break-even using CashFlowService projection
        months_until_break_even = FinancialDashboardService._calculate_break_even()

        return {
            "current_month_balance": current_month_balance,
            "current_month_income": current_month_income,
            "current_month_expenses": current_month_expenses,
            "total_debt": total_debt,
            "total_monthly_obligations": total_monthly_obligations,
            "total_monthly_income": total_monthly_income,
            "months_until_break_even": months_until_break_even,
        }

    @staticmethod
    def _calculate_break_even() -> int | None:
        """Calculate months until cumulative balance becomes positive.

        Returns 0 if already positive, None if > 60 months.
        """
        projection = CashFlowService.get_cash_flow_projection(months=MAX_BREAK_EVEN_MONTHS)

        if not projection:
            return None

        # Check if already positive from the start
        if projection[0]["cumulative_balance"] >= 0:
            return 0

        for i, month_data in enumerate(projection):
            if month_data["cumulative_balance"] >= 0:
                return i

        return None

    @staticmethod
    def get_debt_by_person() -> list[dict[str, Any]]:
        """Return debt breakdown per person: card debt, loan debt, monthly amounts."""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        next_month = _next_month_start(today.year, today.month)

        # Get persons who have expenses with installments
        persons_with_expenses = Person.objects.filter(
            expenses__installments__isnull=False,
        ).distinct()

        result = []
        for person in persons_with_expenses:
            unpaid_installments = ExpenseInstallment.objects.filter(
                expense__person=person,
                is_paid=False,
                expense__is_offset=False,
            )

            card_debt = unpaid_installments.filter(
                expense__expense_type=ExpenseType.CARD_PURCHASE,
            ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

            loan_debt = unpaid_installments.filter(
                expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
            ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

            # Monthly amounts (this month only, excluding offsets)
            monthly_card = ExpenseInstallment.objects.filter(
                expense__person=person,
                expense__expense_type=ExpenseType.CARD_PURCHASE,
                expense__is_offset=False,
                due_date__gte=month_start,
                due_date__lt=next_month,
                is_paid=False,
            ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

            monthly_loan = ExpenseInstallment.objects.filter(
                expense__person=person,
                expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
                expense__is_offset=False,
                due_date__gte=month_start,
                due_date__lt=next_month,
                is_paid=False,
            ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

            cards_count = CreditCard.objects.filter(
                person=person,
                is_active=True,
            ).count()

            total_debt = card_debt + loan_debt

            result.append(
                {
                    "person_id": person.id,
                    "person_name": person.name,
                    "card_debt": card_debt,
                    "loan_debt": loan_debt,
                    "total_debt": total_debt,
                    "monthly_card": monthly_card,
                    "monthly_loan": monthly_loan,
                    "cards_count": cards_count,
                }
            )

        return result

    @staticmethod
    def get_debt_by_type() -> dict[str, Decimal]:
        """Return total unpaid debt grouped by expense type."""
        unpaid = ExpenseInstallment.objects.filter(is_paid=False, expense__is_offset=False)

        card_purchases = unpaid.filter(
            expense__expense_type=ExpenseType.CARD_PURCHASE,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        bank_loans = unpaid.filter(
            expense__expense_type=ExpenseType.BANK_LOAN,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        personal_loans = unpaid.filter(
            expense__expense_type=ExpenseType.PERSONAL_LOAN,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        water_debt = unpaid.filter(
            expense__expense_type=ExpenseType.WATER_BILL,
            expense__is_debt_installment=True,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        electricity_debt = unpaid.filter(
            expense__expense_type=ExpenseType.ELECTRICITY_BILL,
            expense__is_debt_installment=True,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        property_tax_debt = unpaid.filter(
            expense__expense_type=ExpenseType.PROPERTY_TAX,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        total = (
            card_purchases
            + bank_loans
            + personal_loans
            + water_debt
            + electricity_debt
            + property_tax_debt
        )

        return {
            "card_purchases": card_purchases,
            "bank_loans": bank_loans,
            "personal_loans": personal_loans,
            "water_debt": water_debt,
            "electricity_debt": electricity_debt,
            "property_tax_debt": property_tax_debt,
            "total": total,
        }

    @staticmethod
    def get_upcoming_installments(days: int = 30) -> list[dict[str, Any]]:
        """Return unpaid installments due within the next N days, ordered by due_date."""
        today = date.today()
        end_date = today + timedelta(days=days)

        installments = (
            ExpenseInstallment.objects.filter(
                due_date__gte=today,
                due_date__lte=end_date,
                is_paid=False,
                expense__is_offset=False,
            )
            .select_related("expense", "expense__person", "expense__credit_card")
            .order_by("due_date")
        )

        return [
            {
                "id": inst.id,
                "expense_description": inst.expense.description,
                "expense_type": inst.expense.expense_type,
                "person_name": inst.expense.person.name if inst.expense.person else None,
                "credit_card_nickname": inst.expense.credit_card.nickname
                if inst.expense.credit_card
                else None,
                "installment_number": inst.installment_number,
                "total_installments": inst.total_installments,
                "amount": inst.amount,
                "due_date": inst.due_date,
                "days_until_due": (inst.due_date - today).days,
            }
            for inst in installments
        ]

    @staticmethod
    def get_overdue_installments() -> list[dict[str, Any]]:
        """Return unpaid installments with due_date before today, ordered by due_date."""
        today = date.today()

        installments = (
            ExpenseInstallment.objects.filter(
                due_date__lt=today,
                is_paid=False,
                expense__is_offset=False,
            )
            .select_related("expense", "expense__person", "expense__credit_card")
            .order_by("due_date")
        )

        return [
            {
                "id": inst.id,
                "expense_description": inst.expense.description,
                "expense_type": inst.expense.expense_type,
                "person_name": inst.expense.person.name if inst.expense.person else None,
                "credit_card_nickname": inst.expense.credit_card.nickname
                if inst.expense.credit_card
                else None,
                "installment_number": inst.installment_number,
                "total_installments": inst.total_installments,
                "amount": inst.amount,
                "due_date": inst.due_date,
                "days_overdue": (today - inst.due_date).days,
            }
            for inst in installments
        ]

    @staticmethod
    def get_expense_category_breakdown(year: int, month: int) -> list[dict[str, Any]]:
        """Return expense totals grouped by category for a given month."""
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        expenses_in_month = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=next_month,
            is_offset=False,
        )

        # Get grand total for percentage calculation
        grand_total = expenses_in_month.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"]

        if grand_total == Decimal("0.00"):
            return []

        # Group by category
        category_data = (
            expenses_in_month.values("category__id", "category__name", "category__color")
            .annotate(
                total=Sum("total_amount"),
                count=Count("id"),
            )
            .order_by("-total")
        )

        result = []
        for item in category_data:
            category_id = item["category__id"]
            category_name = item["category__name"] or "Sem Categoria"
            color = item["category__color"] or "#6B7280"
            total = item["total"]
            percentage = float(total / grand_total * 100)

            result.append(
                {
                    "category_id": category_id,
                    "category_name": category_name,
                    "color": color,
                    "total": total,
                    "percentage": round(percentage, 2),
                    "count": item["count"],
                }
            )

        return result
