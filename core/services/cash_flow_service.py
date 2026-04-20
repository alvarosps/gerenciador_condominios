"""
Cash flow service for financial module.

Provides monthly income/expense calculations, cash flow projection,
and per-person financial summaries.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Avg, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.cache import cache_result
from core.models import (
    Apartment,
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    ExpenseType,
    FinancialSettings,
    Income,
    Lease,
    MonthSnapshot,
    Person,
    PersonIncome,
    PersonIncomeType,
    PersonPayment,
    RentPayment,
)
from core.services.date_calculator import DateCalculatorService

MONTHS_IN_YEAR = 12
UTILITY_LOOKBACK_MONTHS = 3


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
        next_month = DateCalculatorService.next_month_start(year, month)

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
        """Collect owner repayment amounts and details for leases active in the given month."""
        owner_leases = (
            Lease.objects.filter(
                apartment__is_rented=True,
                apartment__owner__isnull=False,
            )
            .filter(start_date__lte=month_start)
            .exclude(prepaid_until__gte=month_start)
            .exclude(is_salary_offset=True)
            .select_related("apartment", "apartment__owner", "apartment__building")
        )

        owner_repayments = Decimal("0.00")
        details = []
        for lease in owner_leases:
            owner_repayments += lease.rental_value
            owner = lease.apartment.owner
            details.append(
                {
                    "person_name": owner.name if owner is not None else "",
                    "apartment_number": str(lease.apartment.number),
                    "building_name": lease.apartment.building.street_number,
                    "amount": lease.rental_value,
                }
            )
        return owner_repayments, details

    @staticmethod
    def _collect_person_stipends(month_start: date) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect fixed stipend amounts and details, filtered to stipends active in the given month."""
        stipends = (
            PersonIncome.objects.filter(
                income_type=PersonIncomeType.FIXED_STIPEND,
                is_active=True,
            )
            .filter(start_date__lte=month_start)
            .exclude(end_date__lt=month_start)
            .select_related("person")
        )

        person_stipends = Decimal("0.00")
        details = []
        for stipend in stipends:
            amount = stipend.fixed_amount or Decimal("0.00")
            person_stipends += amount
            details.append({"person_name": stipend.person.name, "amount": amount})
        return person_stipends, details

    @staticmethod
    def _collect_installments(
        month_start: date,
        next_month: date,
        expense_filter: Q,
        skipped_expense_ids: set[int],
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Generic installment collector for a given expense filter.

        Returns total amount and a list of detail dicts with keys:
        description, person_name, card_name, installment, amount, due_date.
        person_name and card_name are None when not applicable.
        """
        qs = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
            )
            .filter(expense_filter)
            .exclude(expense_id__in=skipped_expense_ids)
            .select_related("expense", "expense__person", "expense__credit_card")
        )

        total = Decimal("0.00")
        details = []
        for inst in qs:
            total += inst.amount
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
        return total, details

    @staticmethod
    def _collect_card_installments(
        month_start: date, next_month: date, skipped_expense_ids: set[int]
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect card installment amounts and details."""
        return CashFlowService._collect_installments(
            month_start,
            next_month,
            Q(
                expense__expense_type=ExpenseType.CARD_PURCHASE,
                expense__is_debt_installment=False,
                expense__is_offset=False,
            ),
            skipped_expense_ids,
        )

    @staticmethod
    def _collect_loan_installments(
        month_start: date, next_month: date, skipped_expense_ids: set[int]
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect loan installment amounts and details."""
        return CashFlowService._collect_installments(
            month_start,
            next_month,
            Q(
                expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
                expense__is_offset=False,
            ),
            skipped_expense_ids,
        )

    @staticmethod
    def _collect_utility_bills(
        month_start: date, next_month: date, skipped_expense_ids: set[int]
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect utility bill amounts and details."""
        qs = (
            Expense.objects.filter(
                expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
                is_debt_installment=False,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            )
            .exclude(pk__in=skipped_expense_ids)
            .select_related("building")
        )

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
        month_start: date, next_month: date, skipped_expense_ids: set[int]
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect debt installment amounts and details."""
        return CashFlowService._collect_installments(
            month_start,
            next_month,
            Q(expense__is_debt_installment=True),
            skipped_expense_ids,
        )

    @staticmethod
    def _collect_property_tax(
        month_start: date, next_month: date, skipped_expense_ids: set[int]
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect property tax installment amounts and details."""
        return CashFlowService._collect_installments(
            month_start,
            next_month,
            Q(expense__expense_type=ExpenseType.PROPERTY_TAX),
            skipped_expense_ids,
        )

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
    def _collect_fixed_expenses(
        month_start: date,
        skipped_expense_ids: set[int],
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect fixed recurring expense amounts and details."""
        qs = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                is_offset=False,
                expected_monthly_amount__isnull=False,
            )
            .exclude(end_date__lt=month_start)
            .exclude(pk__in=skipped_expense_ids)
            .select_related("person")
        )

        fixed_expenses = Decimal("0.00")
        details = []
        for exp in qs:
            amount = exp.expected_monthly_amount or Decimal("0.00")
            fixed_expenses += amount
            details.append(
                {
                    "description": exp.description,
                    "amount": amount,
                    "person_name": exp.person.name if exp.person else None,
                }
            )
        return fixed_expenses, details

    @staticmethod
    def _collect_one_time_expenses(
        month_start: date, next_month: date, skipped_expense_ids: set[int]
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect one-time expense amounts and details."""
        qs = Expense.objects.filter(
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            is_offset=False,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).exclude(pk__in=skipped_expense_ids)

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
        next_month = DateCalculatorService.next_month_start(year, month)

        skipped_expense_ids: set[int] = set(
            ExpenseMonthSkip.objects.filter(
                reference_month=month_start,
            ).values_list("expense_id", flat=True)
        )

        owner_repayments, owner_repayments_details = CashFlowService._collect_owner_repayments(
            month_start, next_month
        )
        person_stipends, person_stipends_details = CashFlowService._collect_person_stipends(
            month_start
        )
        card_installments, card_installments_details = CashFlowService._collect_card_installments(
            month_start, next_month, skipped_expense_ids
        )
        loan_installments, loan_installments_details = CashFlowService._collect_loan_installments(
            month_start, next_month, skipped_expense_ids
        )
        utility_bills, utility_bills_details = CashFlowService._collect_utility_bills(
            month_start, next_month, skipped_expense_ids
        )
        debt_installments, debt_installments_details = CashFlowService._collect_debt_installments(
            month_start, next_month, skipped_expense_ids
        )
        property_tax, property_tax_details = CashFlowService._collect_property_tax(
            month_start, next_month, skipped_expense_ids
        )
        employee_salary, employee_salary_details = CashFlowService._collect_employee_salary(
            month_start
        )
        fixed_expenses, fixed_expenses_details = CashFlowService._collect_fixed_expenses(
            month_start, skipped_expense_ids
        )
        one_time_expenses, one_time_expenses_details = CashFlowService._collect_one_time_expenses(
            month_start, next_month, skipped_expense_ids
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
    @cache_result(timeout=300, key_prefix="cash-flow-projection")
    def get_cash_flow_projection(
        months: int = 12,
        *,
        full_occupancy_future: bool = False,
        full_occupancy_current: bool = False,
        extra_monthly_expenses: Decimal = Decimal("0.00"),
    ) -> list[dict[str, Any]]:
        """
        Project cash flow for N months starting from the current month.

        For future months without registered data:
        - Rents: Active leases projected (same income logic, no RentPayment check)
        - Installments: Known ExpenseInstallments with future due_date
        - Utility bills: Average of last 3 registered months per building/type
        - Fixed expenses: expected_monthly_amount
        - Recurring income: expected_monthly_amount

        Simulation options:
        - full_occupancy_future: assume all apartments are rented in future months
        - full_occupancy_current: assume all apartments are rented in current month too
        - extra_monthly_expenses: add a fixed amount to monthly expenses (groceries, etc.)
        """
        today = timezone.now().date()
        current_year = today.year
        current_month = today.month
        current_month_date = date(current_year, current_month, 1)

        # Get initial balance from FinancialSettings
        settings = FinancialSettings.objects.first()
        initial_balance = settings.initial_balance if settings else Decimal("0.00")

        # Pre-calculate full occupancy bonus once (if needed)
        full_occupancy_bonus = Decimal("0.00")
        if full_occupancy_future or full_occupancy_current:
            full_occupancy_bonus = CashFlowService._get_full_occupancy_bonus()

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
            is_projected = target_date > current_month_date
            is_current = target_date == current_month_date

            snapshot = MonthSnapshot.objects.filter(
                reference_month=target_date,
                is_finalized=True,
            ).first()

            if snapshot is not None:
                projection.append(
                    {
                        "year": year,
                        "month": month,
                        "income_total": str(snapshot.total_income),
                        "expenses_total": str(snapshot.total_expenses),
                        "balance": str(snapshot.net_balance),
                        "cumulative_balance": str(snapshot.cumulative_ending_balance),
                        "is_projected": is_projected,
                        "is_snapshot": True,
                    }
                )
                cumulative_balance = Decimal(str(snapshot.cumulative_ending_balance))
                continue

            if is_projected:
                income_total = CashFlowService._get_projected_income(year, month)
                expenses_total = CashFlowService._get_projected_expenses(year, month)
            else:
                cash_flow = CashFlowService.get_monthly_cash_flow(year, month)
                income_total = cash_flow["income"]["total"]
                expenses_total = cash_flow["expenses"]["total"]

            # Apply simulation adjustments
            apply_occupancy = (is_projected and full_occupancy_future) or (
                is_current and full_occupancy_current
            )
            if apply_occupancy:
                income_total += full_occupancy_bonus

            if extra_monthly_expenses > 0:
                expenses_total += extra_monthly_expenses

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
    def _get_full_occupancy_bonus() -> Decimal:
        """Calculate additional rent income if all vacant apartments were rented.

        Uses the average rental value of currently rented apartments as estimate
        for vacant ones.
        """
        vacant_apartments = Apartment.objects.filter(
            is_rented=False,
            owner__isnull=True,
        )
        vacant_count = vacant_apartments.count()
        if vacant_count == 0:
            return Decimal("0.00")

        # Average rent from currently occupied apartments (excluding owner/salary offset)
        rented_leases = Lease.objects.filter(
            apartment__is_rented=True,
            apartment__owner__isnull=True,
            is_salary_offset=False,
        )
        if not rented_leases.exists():
            return Decimal("0.00")

        avg_rent: Decimal = rented_leases.aggregate(
            avg=Coalesce(Avg("rental_value"), Decimal("0.00"))
        )["avg"]

        return avg_rent * vacant_count

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
        recurring_income: Decimal = Income.objects.filter(
            is_recurring=True,
            expected_monthly_amount__isnull=False,
        ).aggregate(total=Coalesce(Sum("expected_monthly_amount"), Decimal("0.00")))["total"]

        return rent_income + recurring_income

    @staticmethod
    def _get_projected_expenses(year: int, month: int) -> Decimal:
        """Calculate projected expenses for a future month."""
        month_start = date(year, month, 1)
        next_month = DateCalculatorService.next_month_start(year, month)

        total = Decimal("0.00")

        # Owner repayments — exclude prepaid and salary-offset leases
        owner_total = Decimal("0.00")
        owner_leases = (
            Lease.objects.filter(
                apartment__is_rented=True,
                apartment__owner__isnull=False,
            )
            .exclude(prepaid_until__gte=month_start)
            .exclude(is_salary_offset=True)
        )
        for lease in owner_leases:
            owner_total += lease.rental_value
        total += owner_total

        # Person stipends — filter to active range only (same logic as _collect_person_stipends)
        stipend_total: Decimal = (
            PersonIncome.objects.filter(
                income_type=PersonIncomeType.FIXED_STIPEND,
                is_active=True,
                fixed_amount__isnull=False,
                start_date__lte=month_start,
            )
            .exclude(end_date__lt=month_start)
            .aggregate(total=Coalesce(Sum("fixed_amount"), Decimal("0.00")))["total"]
        )
        total += stipend_total

        # Known installments (card, loan, debt, property_tax) with due_date in month
        installment_total: Decimal = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__is_offset=False,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        total += installment_total

        # Utility bills — average of last 3 months
        total += CashFlowService._get_projected_utility_average()

        # Fixed expenses (respect end_date and exclude offsets)
        fixed_total: Decimal = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                is_offset=False,
                expected_monthly_amount__isnull=False,
            )
            .exclude(end_date__lt=month_start)
            .aggregate(total=Coalesce(Sum("expected_monthly_amount"), Decimal("0.00")))["total"]
        )
        total += fixed_total

        # Employee salary — use latest payment per person as projection (avoids N+1).
        # Step 1: for each person get the pk of their most-recent payment (one query).
        # Step 2: fetch those payments in bulk (one query).
        latest_pk_per_person = (
            EmployeePayment.objects.values("person")
            .annotate(max_pk=Max("pk"))
            .values_list("max_pk", flat=True)
        )
        latest_payments = EmployeePayment.objects.filter(pk__in=latest_pk_per_person)
        for ep in latest_payments:
            total += ep.total_paid

        return total

    @staticmethod
    def _get_projected_utility_average() -> Decimal:
        """Get average utility bill from the last 3 months of data."""
        utility_expenses = Expense.objects.filter(
            expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
            is_debt_installment=False,
            is_offset=False,
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
            m_end = DateCalculatorService.next_month_start(y, m)
            month_filters |= Q(expense_date__gte=m_start, expense_date__lt=m_end)

        monthly_totals: Decimal = (
            Expense.objects.filter(
                expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
                is_debt_installment=False,
                is_offset=False,
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
        next_month = DateCalculatorService.next_month_start(year, month)

        skipped_expense_ids: set[int] = set(
            ExpenseMonthSkip.objects.filter(
                reference_month=month_start,
            ).values_list("expense_id", flat=True)
        )

        # Receives: rent from owned apartments
        receives = Decimal("0.00")
        receives_details = []

        owned_apartments = Apartment.objects.filter(owner=person, is_rented=True).select_related(
            "building"
        )

        for apt in owned_apartments:
            lease = apt.leases.filter(is_deleted=False).first()
            if lease is not None:
                receives += lease.rental_value
                receives_details.append(
                    {
                        "apartment_number": str(apt.number),
                        "building_name": apt.building.street_number,
                        "rental_value": lease.rental_value,
                        "source": "apartment_rent",
                    }
                )

        # Receives: fixed stipends — filter to active range only
        stipends = PersonIncome.objects.filter(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
            start_date__lte=month_start,
        ).exclude(end_date__lt=month_start)
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

        # Card installments for this person (excluding offsets and skipped months)
        card_installments = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__expense_type=ExpenseType.CARD_PURCHASE,
                expense__is_debt_installment=False,
                expense__is_offset=False,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .select_related("expense", "expense__credit_card")
        )

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

        # Loan installments for this person (excluding offsets and skipped months)
        loan_installments = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
                expense__is_offset=False,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .select_related("expense")
        )

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

        # Offset installments (discounts — purchases on this person's card that are for sogros/Camila)
        offset_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__person=person,
            expense__is_offset=True,
        ).select_related("expense")

        offset_total = Decimal("0.00")
        offset_details = []
        for inst in offset_installments:
            offset_total += inst.amount
            offset_details.append(
                {
                    "description": inst.expense.description,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
            )

        # Also check non-installment offset expenses for this month
        offset_single = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=next_month,
            person=person,
            is_offset=True,
            is_installment=False,
        )
        for exp in offset_single:
            offset_total += exp.total_amount
            offset_details.append(
                {
                    "description": exp.description,
                    "installment": None,
                    "amount": exp.total_amount,
                    "due_date": exp.expense_date,
                }
            )

        # Fixed expenses for this person (recurring monthly charges, excluding skipped months)
        fixed_for_person = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                person=person,
                is_offset=False,
            )
            .exclude(end_date__lt=month_start)
            .exclude(pk__in=skipped_expense_ids)
        )

        fixed_total = Decimal("0.00")
        fixed_details = []
        for exp in fixed_for_person:
            amount = exp.expected_monthly_amount or exp.total_amount
            fixed_total += amount
            fixed_details.append(
                {
                    "description": exp.description,
                    "amount": amount,
                }
            )

        net_amount = receives - card_total - loan_total - fixed_total + offset_total

        # Payments made to this person for this month
        payments = PersonPayment.objects.filter(
            person=person,
            reference_month=month_start,
        ).order_by("payment_date")

        total_paid = Decimal("0.00")
        payment_details = []
        for payment in payments:
            total_paid += payment.amount
            payment_details.append(
                {
                    "amount": payment.amount,
                    "payment_date": payment.payment_date,
                    "notes": payment.notes,
                }
            )

        pending_balance = net_amount - total_paid

        return {
            "person_id": person_id,
            "person_name": person.name,
            "receives": receives,
            "receives_details": receives_details,
            "card_total": card_total,
            "card_details": card_details,
            "loan_total": loan_total,
            "loan_details": loan_details,
            "fixed_total": fixed_total,
            "fixed_details": fixed_details,
            "offset_total": offset_total,
            "offset_details": offset_details,
            "net_amount": net_amount,
            "total_paid": total_paid,
            "payment_details": payment_details,
            "pending_balance": pending_balance,
        }
