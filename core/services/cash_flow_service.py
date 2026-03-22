"""
Cash flow service for financial module.

Provides monthly income/expense calculations, cash flow projection,
and per-person financial summaries.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Max, Q, Sum
from django.db.models.functions import Coalesce

from core.models import (
    Apartment,
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    FinancialSettings,
    Income,
    Lease,
    Person,
    PersonIncome,
    PersonIncomeType,
    RentPayment,
)

MONTHS_IN_YEAR = 12
UTILITY_LOOKBACK_MONTHS = 3


def _next_month_start(year: int, month: int) -> date:
    """Return the first day of the month following (year, month)."""
    if month == MONTHS_IN_YEAR:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


class CashFlowService:
    """Service for cash flow calculations — monthly income, expenses, projections, and person summaries."""

    @staticmethod
    def get_monthly_income(year: int, month: int) -> dict[str, Any]:
        """
        Calculate income for a given month.

        Excludes:
        - Apartments with owner (rent goes to owner, not condominium)
        - Leases with prepaid_until >= queried month
        - Leases with is_salary_offset=True
        """
        reference_date = date(year, month, 1)

        # Active leases excluding owner apartments, prepaid, and salary offset
        leases = (
            Lease.objects.filter(apartment__is_rented=True)
            .filter(apartment__owner__isnull=True)
            .exclude(prepaid_until__gte=reference_date)
            .exclude(is_salary_offset=True)
            .select_related("apartment", "apartment__building", "responsible_tenant")
        )

        # Get rent payments for this month
        rent_payments = {
            rp.lease_id: rp
            for rp in RentPayment.objects.filter(reference_month=reference_date).select_related(
                "lease"
            )
        }

        rent_income = Decimal("0.00")
        rent_details = []

        for lease in leases:
            rent_income += lease.rental_value
            payment = rent_payments.get(lease.id)
            rent_details.append(
                {
                    "apartment_id": lease.apartment_id,
                    "apartment_number": str(lease.apartment.number),
                    "building_name": lease.apartment.building.street_number,
                    "tenant_name": lease.responsible_tenant.name,
                    "rental_value": lease.rental_value,
                    "is_paid": payment is not None,
                    "payment_date": payment.payment_date if payment else None,
                }
            )

        # Extra income: received in the month + recurring projections
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        # One-time/non-recurring income received this month
        received_income = Income.objects.filter(
            income_date__gte=month_start,
            income_date__lt=next_month,
            is_received=True,
            is_recurring=False,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        # Recurring income projections
        recurring_income = Income.objects.filter(
            is_recurring=True,
            expected_monthly_amount__isnull=False,
        ).aggregate(total=Coalesce(Sum("expected_monthly_amount"), Decimal("0.00")))["total"]

        extra_income = received_income + recurring_income

        # Extra income details
        non_recurring = Income.objects.filter(
            income_date__gte=month_start,
            income_date__lt=next_month,
            is_received=True,
            is_recurring=False,
        )
        extra_income_details = [
            {
                "description": inc.description,
                "amount": inc.amount,
                "income_date": inc.income_date,
                "is_recurring": False,
            }
            for inc in non_recurring
        ]

        recurring = Income.objects.filter(
            is_recurring=True,
            expected_monthly_amount__isnull=False,
        )
        extra_income_details.extend(
            {
                "description": inc.description,
                "amount": inc.expected_monthly_amount,
                "income_date": inc.income_date,
                "is_recurring": True,
            }
            for inc in recurring
        )

        total = rent_income + extra_income

        return {
            "rent_income": rent_income,
            "rent_details": rent_details,
            "extra_income": extra_income,
            "extra_income_details": extra_income_details,
            "total": total,
        }

    @staticmethod
    def _collect_owner_repayments(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect owner repayment amounts and details."""
        owner_leases = Lease.objects.filter(
            apartment__is_rented=True,
            apartment__owner__isnull=False,
        ).select_related("apartment", "apartment__owner", "apartment__building")

        owner_repayments = Decimal("0.00")
        details = []
        for lease in owner_leases:
            owner_repayments += lease.rental_value
            details.append(
                {
                    "person_name": lease.apartment.owner.name,
                    "apartment_number": str(lease.apartment.number),
                    "building_name": lease.apartment.building.street_number,
                    "amount": lease.rental_value,
                }
            )
        return owner_repayments, details

    @staticmethod
    def _collect_person_stipends() -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect fixed stipend amounts and details."""
        stipends = PersonIncome.objects.filter(
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
        ).select_related("person")

        person_stipends = Decimal("0.00")
        details = []
        for stipend in stipends:
            amount = stipend.fixed_amount or Decimal("0.00")
            person_stipends += amount
            details.append({"person_name": stipend.person.name, "amount": amount})
        return person_stipends, details

    @staticmethod
    def _collect_card_installments(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect card installment amounts and details."""
        qs = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__expense_type=ExpenseType.CARD_PURCHASE,
            expense__is_debt_installment=False,
        ).select_related("expense", "expense__person", "expense__credit_card")

        card_installments = Decimal("0.00")
        details = []
        for inst in qs:
            card_installments += inst.amount
            details.append(
                {
                    "description": inst.expense.description,
                    "person_name": inst.expense.person.name if inst.expense.person else None,
                    "card_name": inst.expense.credit_card.nickname
                    if inst.expense.credit_card
                    else None,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )
        return card_installments, details

    @staticmethod
    def _collect_loan_installments(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect loan installment amounts and details."""
        qs = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
        ).select_related("expense", "expense__person")

        loan_installments = Decimal("0.00")
        details = []
        for inst in qs:
            loan_installments += inst.amount
            details.append(
                {
                    "description": inst.expense.description,
                    "person_name": inst.expense.person.name if inst.expense.person else None,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )
        return loan_installments, details

    @staticmethod
    def _collect_utility_bills(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect utility bill amounts and details."""
        qs = Expense.objects.filter(
            expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
            is_debt_installment=False,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).select_related("building")

        utility_bills = Decimal("0.00")
        details = []
        for exp in qs:
            utility_bills += exp.total_amount
            details.append(
                {
                    "description": exp.description,
                    "expense_type": exp.expense_type,
                    "building_name": exp.building.street_number if exp.building else None,
                    "amount": exp.total_amount,
                    "expense_date": exp.expense_date,
                }
            )
        return utility_bills, details

    @staticmethod
    def _collect_debt_installments(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect debt installment amounts and details."""
        qs = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__is_debt_installment=True,
        ).select_related("expense", "expense__person")

        debt_installments = Decimal("0.00")
        details = []
        for inst in qs:
            debt_installments += inst.amount
            details.append(
                {
                    "description": inst.expense.description,
                    "person_name": inst.expense.person.name if inst.expense.person else None,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )
        return debt_installments, details

    @staticmethod
    def _collect_property_tax(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect property tax installment amounts and details."""
        qs = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__expense_type=ExpenseType.PROPERTY_TAX,
        ).select_related("expense")

        property_tax = Decimal("0.00")
        details = []
        for inst in qs:
            property_tax += inst.amount
            details.append(
                {
                    "description": inst.expense.description,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )
        return property_tax, details

    @staticmethod
    def _collect_employee_salary(month_start: date) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect employee salary amounts and details."""
        employee_payments = EmployeePayment.objects.filter(
            reference_month=month_start,
        ).select_related("person")

        employee_salary = Decimal("0.00")
        details = []
        for ep in employee_payments:
            total = ep.total_paid
            employee_salary += total
            details.append(
                {
                    "person_name": ep.person.name,
                    "base_salary": ep.base_salary,
                    "variable_amount": ep.variable_amount,
                    "total_paid": total,
                }
            )
        return employee_salary, details

    @staticmethod
    def _collect_fixed_expenses() -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect fixed recurring expense amounts and details."""
        qs = Expense.objects.filter(
            expense_type=ExpenseType.FIXED_EXPENSE,
            is_recurring=True,
            expected_monthly_amount__isnull=False,
        )

        fixed_expenses = Decimal("0.00")
        details = []
        for exp in qs:
            amount = exp.expected_monthly_amount or Decimal("0.00")
            fixed_expenses += amount
            details.append({"description": exp.description, "amount": amount})
        return fixed_expenses, details

    @staticmethod
    def _collect_one_time_expenses(
        month_start: date, next_month: date
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect one-time expense amounts and details."""
        qs = Expense.objects.filter(
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        )

        one_time_expenses = Decimal("0.00")
        details = []
        for exp in qs:
            one_time_expenses += exp.total_amount
            details.append(
                {
                    "description": exp.description,
                    "amount": exp.total_amount,
                    "expense_date": exp.expense_date,
                }
            )
        return one_time_expenses, details

    @staticmethod
    def get_monthly_expenses(year: int, month: int) -> dict[str, Any]:
        """Calculate expenses for a given month across all 10 categories."""
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        owner_repayments, owner_repayments_details = CashFlowService._collect_owner_repayments(
            month_start, next_month
        )
        person_stipends, person_stipends_details = CashFlowService._collect_person_stipends()
        card_installments, card_installments_details = CashFlowService._collect_card_installments(
            month_start, next_month
        )
        loan_installments, loan_installments_details = CashFlowService._collect_loan_installments(
            month_start, next_month
        )
        utility_bills, utility_bills_details = CashFlowService._collect_utility_bills(
            month_start, next_month
        )
        debt_installments, debt_installments_details = CashFlowService._collect_debt_installments(
            month_start, next_month
        )
        property_tax, property_tax_details = CashFlowService._collect_property_tax(
            month_start, next_month
        )
        employee_salary, employee_salary_details = CashFlowService._collect_employee_salary(
            month_start
        )
        fixed_expenses, fixed_expenses_details = CashFlowService._collect_fixed_expenses()
        one_time_expenses, one_time_expenses_details = CashFlowService._collect_one_time_expenses(
            month_start, next_month
        )

        total = (
            owner_repayments
            + person_stipends
            + card_installments
            + loan_installments
            + utility_bills
            + debt_installments
            + property_tax
            + employee_salary
            + fixed_expenses
            + one_time_expenses
        )

        return {
            "owner_repayments": owner_repayments,
            "owner_repayments_details": owner_repayments_details,
            "person_stipends": person_stipends,
            "person_stipends_details": person_stipends_details,
            "card_installments": card_installments,
            "card_installments_details": card_installments_details,
            "loan_installments": loan_installments,
            "loan_installments_details": loan_installments_details,
            "utility_bills": utility_bills,
            "utility_bills_details": utility_bills_details,
            "debt_installments": debt_installments,
            "debt_installments_details": debt_installments_details,
            "property_tax": property_tax,
            "property_tax_details": property_tax_details,
            "employee_salary": employee_salary,
            "employee_salary_details": employee_salary_details,
            "fixed_expenses": fixed_expenses,
            "fixed_expenses_details": fixed_expenses_details,
            "one_time_expenses": one_time_expenses,
            "one_time_expenses_details": one_time_expenses_details,
            "total": total,
        }

    @staticmethod
    def get_monthly_cash_flow(year: int, month: int) -> dict[str, Any]:
        """Calculate monthly cash flow: income - expenses = balance."""
        income = CashFlowService.get_monthly_income(year, month)
        expenses = CashFlowService.get_monthly_expenses(year, month)

        return {
            "year": year,
            "month": month,
            "income": income,
            "expenses": expenses,
            "balance": income["total"] - expenses["total"],
        }

    @staticmethod
    def get_cash_flow_projection(months: int = 12) -> list[dict[str, Any]]:
        """
        Project cash flow for N months starting from the current month.

        For future months without registered data:
        - Rents: Active leases projected (same income logic, no RentPayment check)
        - Installments: Known ExpenseInstallments with future due_date
        - Utility bills: Average of last 3 registered months per building/type
        - Fixed expenses: expected_monthly_amount
        - Recurring income: expected_monthly_amount
        """
        today = date.today()
        current_year = today.year
        current_month = today.month

        # Get initial balance from FinancialSettings
        initial_balance = Decimal("0.00")
        try:
            settings = FinancialSettings.objects.get(pk=1)
            initial_balance = settings.initial_balance
        except FinancialSettings.DoesNotExist:
            pass

        projection = []
        cumulative_balance = initial_balance

        for i in range(months):
            # Calculate target month
            month = current_month + i
            year = current_year
            while month > MONTHS_IN_YEAR:
                month -= MONTHS_IN_YEAR
                year += 1

            target_date = date(year, month, 1)
            is_projected = target_date > date(today.year, today.month, 1)

            if is_projected:
                income_total = CashFlowService._get_projected_income(year, month)
                expenses_total = CashFlowService._get_projected_expenses(year, month)
            else:
                cash_flow = CashFlowService.get_monthly_cash_flow(year, month)
                income_total = cash_flow["income"]["total"]
                expenses_total = cash_flow["expenses"]["total"]

            balance = income_total - expenses_total
            cumulative_balance += balance

            projection.append(
                {
                    "year": year,
                    "month": month,
                    "income_total": income_total,
                    "expenses_total": expenses_total,
                    "balance": balance,
                    "cumulative_balance": cumulative_balance,
                    "is_projected": is_projected,
                }
            )

        return projection

    @staticmethod
    def _get_projected_income(year: int, month: int) -> Decimal:
        """Calculate projected income for a future month."""
        reference_date = date(year, month, 1)

        # Active leases (same exclusions as get_monthly_income, but no payment check)
        rent_income = Decimal("0.00")
        leases = (
            Lease.objects.filter(apartment__is_rented=True)
            .filter(apartment__owner__isnull=True)
            .exclude(prepaid_until__gte=reference_date)
            .exclude(is_salary_offset=True)
        )
        for lease in leases:
            rent_income += lease.rental_value

        # Recurring extra income
        recurring_income = Income.objects.filter(
            is_recurring=True,
            expected_monthly_amount__isnull=False,
        ).aggregate(total=Coalesce(Sum("expected_monthly_amount"), Decimal("0.00")))["total"]

        return rent_income + recurring_income

    @staticmethod
    def _get_projected_expenses(year: int, month: int) -> Decimal:
        """Calculate projected expenses for a future month."""
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        total = Decimal("0.00")

        # Owner repayments
        owner_total = Decimal("0.00")
        owner_leases = Lease.objects.filter(
            apartment__is_rented=True,
            apartment__owner__isnull=False,
        )
        for lease in owner_leases:
            owner_total += lease.rental_value
        total += owner_total

        # Person stipends
        stipend_total = PersonIncome.objects.filter(
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
            fixed_amount__isnull=False,
        ).aggregate(total=Coalesce(Sum("fixed_amount"), Decimal("0.00")))["total"]
        total += stipend_total

        # Known installments (card, loan, debt, property_tax) with due_date in month
        installment_total = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        total += installment_total

        # Utility bills — average of last 3 months
        total += CashFlowService._get_projected_utility_average()

        # Fixed expenses
        fixed_total = Expense.objects.filter(
            expense_type=ExpenseType.FIXED_EXPENSE,
            is_recurring=True,
            expected_monthly_amount__isnull=False,
        ).aggregate(total=Coalesce(Sum("expected_monthly_amount"), Decimal("0.00")))["total"]
        total += fixed_total

        # Employee salary — use latest payment as projection
        latest_month_per_person = EmployeePayment.objects.values("person").annotate(
            latest_month=Max("reference_month")
        )
        for entry in latest_month_per_person:
            ep = EmployeePayment.objects.get(
                person_id=entry["person"],
                reference_month=entry["latest_month"],
            )
            total += ep.total_paid

        return total

    @staticmethod
    def _get_projected_utility_average() -> Decimal:
        """Get average utility bill from the last 3 months of data."""
        utility_expenses = Expense.objects.filter(
            expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
            is_debt_installment=False,
        ).order_by("-expense_date")[:90]  # Last ~3 months of records

        if not utility_expenses:
            return Decimal("0.00")

        # Get unique months
        months_seen = set()
        total = Decimal("0.00")
        for exp in utility_expenses:
            month_key = (exp.expense_date.year, exp.expense_date.month)
            months_seen.add(month_key)
            total += exp.total_amount
            if len(months_seen) >= UTILITY_LOOKBACK_MONTHS:
                break

        if not months_seen:
            return Decimal("0.00")

        # Re-calculate: sum all expenses from those months
        month_filters = Q()
        for y, m in months_seen:
            m_start = date(y, m, 1)
            m_end = _next_month_start(y, m)
            month_filters |= Q(expense_date__gte=m_start, expense_date__lt=m_end)

        monthly_totals = (
            Expense.objects.filter(
                expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
                is_debt_installment=False,
            )
            .filter(month_filters)
            .aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]
        )

        return monthly_totals / Decimal(str(len(months_seen)))

    @staticmethod
    def get_person_summary(person_id: int, year: int, month: int) -> dict[str, Any]:
        """
        Calculate financial summary for a specific person in a given month.

        Includes rent received (if owner), stipends, card installments, and loan installments.
        """
        person = Person.objects.get(pk=person_id)

        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        # Receives: rent from owned apartments
        receives = Decimal("0.00")
        receives_details = []

        owned_apartments = Apartment.objects.filter(owner=person, is_rented=True).select_related(
            "building", "lease"
        )

        for apt in owned_apartments:
            try:
                lease = apt.lease
            except Lease.DoesNotExist:
                pass
            else:
                receives += lease.rental_value
                receives_details.append(
                    {
                        "apartment_number": str(apt.number),
                        "building_name": apt.building.street_number,
                        "rental_value": lease.rental_value,
                        "source": "apartment_rent",
                    }
                )

        # Receives: fixed stipends
        stipends = PersonIncome.objects.filter(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
        )
        for stipend in stipends:
            amount = stipend.fixed_amount or Decimal("0.00")
            receives += amount
            receives_details.append(
                {
                    "description": "Estipêndio fixo",
                    "amount": amount,
                    "source": "fixed_stipend",
                }
            )

        # Card installments for this person
        card_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__person=person,
            expense__expense_type=ExpenseType.CARD_PURCHASE,
            expense__is_debt_installment=False,
        ).select_related("expense", "expense__credit_card")

        card_total = Decimal("0.00")
        card_details = []
        for inst in card_installments:
            card_total += inst.amount
            card_details.append(
                {
                    "description": inst.expense.description,
                    "card_name": inst.expense.credit_card.nickname
                    if inst.expense.credit_card
                    else None,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )

        # Loan installments for this person
        loan_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__person=person,
            expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
        ).select_related("expense")

        loan_total = Decimal("0.00")
        loan_details = []
        for inst in loan_installments:
            loan_total += inst.amount
            loan_details.append(
                {
                    "description": inst.expense.description,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )

        net_amount = receives - card_total - loan_total

        return {
            "person_id": person_id,
            "person_name": person.name,
            "receives": receives,
            "receives_details": receives_details,
            "card_total": card_total,
            "card_details": card_details,
            "loan_total": loan_total,
            "loan_details": loan_details,
            "net_amount": net_amount,
        }
