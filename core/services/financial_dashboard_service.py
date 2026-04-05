"""Financial dashboard service for aggregated financial metrics.

Provides overview, debt breakdowns, upcoming/overdue installments,
and expense category analysis for the financial dashboard widgets.
"""

from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.cache import cache_result
from core.models import (
    Apartment,
    Building,
    CreditCard,
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    ExpenseType,
    FinancialSettings,
    Income,
    Lease,
    Person,
    PersonIncome,
    PersonIncomeType,
    PersonPayment,
)

from .cash_flow_service import MONTHS_IN_YEAR, CashFlowService

MAX_BREAK_EVEN_MONTHS = 60


def _next_month_start(year: int, month: int) -> date:
    """Return the first day of the month following (year, month)."""
    if month == MONTHS_IN_YEAR:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def _resolve_building_label(building: Building | None, description: str) -> str:
    """Resolve a building label from the building FK or description keywords."""
    if building:
        return str(building.street_number)
    desc_lower = description.lower()
    if "sítio" in desc_lower or "sitio" in desc_lower:
        return "Sítio"
    return "Outros"


class FinancialDashboardService:
    """Aggregated financial metrics for dashboard widgets."""

    @staticmethod
    @cache_result(timeout=120, key_prefix="financial-dashboard-overview")
    def get_overview() -> dict[str, Any]:
        """
        Return financial overview with current month balance, debts,
        monthly obligations/income, and months until break-even.
        """
        today = timezone.now().date()
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
    @cache_result(timeout=120, key_prefix="financial-dashboard-debt-person")
    def get_debt_by_person() -> list[dict[str, Any]]:
        """Return debt breakdown per person: card debt, loan debt, monthly amounts."""
        today = timezone.now().date()
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
    @cache_result(timeout=120, key_prefix="financial-dashboard-debt-type")
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
    @cache_result(timeout=120, key_prefix="financial-dashboard-upcoming")
    def get_upcoming_installments(days: int = 30) -> list[dict[str, Any]]:
        """Return unpaid installments due within the next N days, ordered by due_date."""
        today = timezone.now().date()
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
    @cache_result(timeout=120, key_prefix="financial-dashboard-overdue")
    def get_overdue_installments() -> list[dict[str, Any]]:
        """Return unpaid installments with due_date before today, ordered by due_date."""
        today = timezone.now().date()

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
    @cache_result(timeout=120, key_prefix="financial-dashboard-category")
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

    @staticmethod
    @cache_result(timeout=120, key_prefix="financial-dashboard-summary")
    def get_dashboard_summary(year: int, month: int) -> dict[str, Any]:
        """Return consolidated dashboard summary: income breakdown, expense by person, and balance."""
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        skipped_expense_ids: set[int] = set(
            ExpenseMonthSkip.objects.filter(
                reference_month=month_start,
            ).values_list("expense_id", flat=True)
        )

        income_summary = FinancialDashboardService._build_income_summary(month_start)
        expense_summary = FinancialDashboardService._build_expense_summary(
            month_start, next_month, year, month, skipped_expense_ids
        )
        overdue_items = FinancialDashboardService._build_overdue_previous_months(year, month)

        # Calculate totals from the summaries themselves (single source of truth)
        total_income = income_summary["condominium_income"] + income_summary["extra_income_total"]
        monthly_expenses = expense_summary["total"]
        overdue_total = sum((item["amount"] for item in overdue_items), Decimal("0.00"))
        total_expenses = monthly_expenses + overdue_total

        return {
            "year": year,
            "month": month,
            "overdue_items": overdue_items,
            "overdue_total": overdue_total,
            "income_summary": income_summary,
            "expense_summary": expense_summary,
            "current_month_income": total_income,
            "current_month_expenses": total_expenses,
            "monthly_expenses": monthly_expenses,
            "current_month_balance": total_income - total_expenses,
        }

    @staticmethod
    def _get_person_waterfall(
        person: Person,
        current_year: int,
        current_month: int,
        lookback_months: int = 6,
    ) -> dict[str, dict[str, Any]]:
        """Calculate payment allocation using waterfall: oldest debt first.

        Returns dict keyed by "YYYY-MM" with {expense_total, allocated_paid, pending} per month.
        Only considers months from FinancialSettings.initial_balance_date onwards.
        """
        # Determine start date from FinancialSettings
        settings = FinancialSettings.objects.first()
        start_date = (
            settings.initial_balance_date if settings else date(current_year, current_month, 1)
        )

        # Build list of months: from start_date to current (oldest first)
        months: list[tuple[int, int]] = []
        y, m = current_year, current_month
        for _ in range(lookback_months):
            m -= 1
            if m == 0:
                m = MONTHS_IN_YEAR
                y -= 1
            if date(y, m, 1) >= start_date:
                months.append((y, m))
        months.reverse()  # oldest first
        months.append((current_year, current_month))

        # Prepend initial_balance as the first month if the person has one
        # and it falls before the lookback window
        initial_balance_entry: dict[str, Any] | None = None
        if (
            person.initial_balance > Decimal("0.00")
            and person.initial_balance_date
            and (person.initial_balance_date.year, person.initial_balance_date.month) not in months
        ):
            ib_y, ib_m = person.initial_balance_date.year, person.initial_balance_date.month
            if date(ib_y, ib_m, 1) < date(current_year, current_month, 1):
                initial_balance_entry = {
                    "year": ib_y,
                    "month": ib_m,
                    "expense_total": person.initial_balance,
                }

        # Get expense total per month
        month_data: list[dict[str, Any]] = []
        if initial_balance_entry:
            month_data.append(initial_balance_entry)
        for y, m in months:
            month_start = date(y, m, 1)
            next_m = _next_month_start(y, m)
            expense_total = FinancialDashboardService._calc_person_expense_total(
                person, month_start, next_m
            )
            month_data.append({"year": y, "month": m, "expense_total": expense_total})

        # Total payments for this person (all time, regardless of reference_month)
        total_payments = PersonPayment.objects.filter(
            person=person,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        # Allocate payments oldest-first
        remaining_payment = total_payments
        result: dict[str, dict[str, Any]] = {}
        for md in month_data:
            key = f"{md['year']}-{md['month']:02d}"
            expense = md["expense_total"]
            allocated = min(remaining_payment, expense)
            remaining_payment -= allocated
            result[key] = {
                "expense_total": expense,
                "allocated_paid": allocated,
                "pending": expense - allocated,
            }

        return result

    @staticmethod
    def _calc_person_expense_total(person: Person, month_start: date, next_month: date) -> Decimal:
        """Calculate total expenses for a person in a month (quick version, no details)."""
        skipped_expense_ids: set[int] = set(
            ExpenseMonthSkip.objects.filter(
                reference_month=month_start,
            ).values_list("expense_id", flat=True)
        )

        card: Decimal = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__expense_type=ExpenseType.CARD_PURCHASE,
                expense__is_debt_installment=False,
                expense__is_offset=False,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        )

        # Single-payment card purchases
        card_single: Decimal = (
            Expense.objects.filter(
                expense_type=ExpenseType.CARD_PURCHASE,
                person=person,
                is_installment=False,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            )
            .exclude(pk__in=skipped_expense_ids)
            .aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]
        )

        loans: Decimal = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
                expense__is_offset=False,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        )

        # Single-payment loans
        loan_single: Decimal = (
            Expense.objects.filter(
                expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
                person=person,
                is_installment=False,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            )
            .exclude(pk__in=skipped_expense_ids)
            .aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]
        )

        fixed: Decimal = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                person=person,
                is_offset=False,
            )
            .exclude(end_date__lt=month_start)
            .exclude(pk__in=skipped_expense_ids)
            .aggregate(total=Coalesce(Sum("expected_monthly_amount"), Decimal("0.00")))["total"]
        )

        one_time: Decimal = (
            Expense.objects.filter(
                expense_type=ExpenseType.ONE_TIME_EXPENSE,
                person=person,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            )
            .exclude(pk__in=skipped_expense_ids)
            .aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]
        )

        offset_inst: Decimal = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__person=person,
            expense__is_offset=True,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        offset_single: Decimal = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=next_month,
            person=person,
            is_offset=True,
            is_installment=False,
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]

        stipends: Decimal = (
            PersonIncome.objects.filter(
                person=person,
                income_type=PersonIncomeType.FIXED_STIPEND,
                is_active=True,
                start_date__lte=month_start,
            )
            .exclude(end_date__lt=month_start)
            .aggregate(total=Coalesce(Sum("fixed_amount"), Decimal("0.00")))["total"]
        )

        return (
            card
            + card_single
            + loans
            + loan_single
            + fixed
            + one_time
            + stipends
            - offset_inst
            - offset_single
        )

    @staticmethod
    def _build_overdue_previous_months(
        current_year: int, current_month: int, lookback_months: int = 6
    ) -> list[dict[str, Any]]:
        """Build list of overdue items from previous months using waterfall payment allocation."""
        overdue: list[dict[str, Any]] = []
        current_month_start = date(current_year, current_month, 1)

        # Person overdue via waterfall allocation
        persons = Person.objects.filter(is_employee=False).order_by("name")
        for person in persons:
            # Skip persons whose expenses are condominium expenses (not payable)
            is_payable = (
                PersonIncome.objects.filter(person=person, is_active=True).exists()
                or Apartment.objects.filter(owner=person).exists()
            )
            if not is_payable:
                continue

            waterfall = FinancialDashboardService._get_person_waterfall(
                person, current_year, current_month, lookback_months
            )

            # Only show previous months with pending > 0
            current_key = f"{current_year}-{current_month:02d}"
            for key, data in waterfall.items():
                if key == current_key:
                    continue  # current month shown in expense cards, not here
                if data["pending"] > Decimal("0.00"):
                    parts = key.split("-")
                    y, m = int(parts[0]), int(parts[1])
                    overdue.append(
                        {
                            "type": "person",
                            "person_id": person.pk,
                            "person_name": person.name,
                            "reference_year": y,
                            "reference_month": m,
                            "amount": data["pending"],
                            "net_amount": data["pending"],
                            "total_paid": data["allocated_paid"],
                        }
                    )

        # Unpaid IPTU installments from previous months
        unpaid_iptu = (
            ExpenseInstallment.objects.filter(
                expense__expense_type=ExpenseType.PROPERTY_TAX,
                due_date__lt=current_month_start,
                is_paid=False,
            )
            .exclude(amount=Decimal("0.00"))
            .select_related("expense", "expense__building")
        )

        overdue.extend(
            {
                "type": "iptu",
                "description": inst.expense.description,
                "building_name": str(inst.expense.building.street_number)
                if inst.expense.building
                else None,
                "reference_year": inst.due_date.year,
                "reference_month": inst.due_date.month,
                "amount": inst.amount,
                "installment": f"{inst.installment_number}/{inst.total_installments}",
                "due_date": inst.due_date.isoformat(),
            }
            for inst in unpaid_iptu
        )

        return overdue

    @staticmethod
    def _build_income_summary(month_start: date) -> dict[str, Any]:
        """Build income breakdown: total, per-owner, vacant, and condominium."""
        total_income = Decimal("0.00")
        all_apartments: list[dict[str, Any]] = []

        # All rented apartments with active leases (including owner apartments)
        rented_apartments = Apartment.objects.filter(is_rented=True).select_related(
            "building", "owner"
        )

        owner_income_map: dict[str, dict[str, Any]] = {}

        salary_offset_total = Decimal("0.00")
        salary_offset_apartments: list[dict[str, Any]] = []

        for apt in rented_apartments:
            lease = apt.leases.filter(is_deleted=False).first()
            if lease is None:
                continue

            rental_value = lease.rental_value

            # Salary offset apartments: rent is compensation, not real income
            if lease.is_salary_offset:
                salary_offset_total += rental_value
                salary_offset_apartments.append(
                    {
                        "apartment_number": str(apt.number),
                        "building_name": apt.building.street_number,
                        "rental_value": rental_value,
                        "tenant_name": lease.responsible_tenant.name,
                    }
                )
                continue

            total_income += rental_value
            apt_info = {
                "apartment_number": str(apt.number),
                "building_name": apt.building.street_number,
                "rental_value": rental_value,
            }
            all_apartments.append(apt_info)

            if apt.owner:
                owner_name = apt.owner.name
                if owner_name not in owner_income_map:
                    owner_income_map[owner_name] = {
                        "person_name": owner_name,
                        "total": Decimal("0.00"),
                        "apartments": [],
                    }
                owner_income_map[owner_name]["total"] += rental_value
                owner_income_map[owner_name]["apartments"].append(str(apt.number))

        # Vacant apartments (not rented) — grouped by building with last known rent
        vacant_apartments = (
            Apartment.objects.filter(is_rented=False)
            .select_related("building", "owner")
            .order_by("building__street_number", "number")
        )
        vacant_lost_rent = Decimal("0.00")
        vacant_by_building: dict[str, list[str]] = {}
        vacant_list: list[dict[str, Any]] = []
        for apt in vacant_apartments:
            rental_value = apt.rental_value
            vacant_lost_rent += rental_value
            building_name = str(apt.building.street_number)
            if building_name not in vacant_by_building:
                vacant_by_building[building_name] = []
            vacant_by_building[building_name].append(str(apt.number))
            vacant_list.append(
                {
                    "apartment_number": str(apt.number),
                    "building_name": building_name,
                    "rental_value": rental_value,
                    "owner_name": apt.owner.name if apt.owner else None,
                }
            )

        vacant_by_building_list = [
            {"building_name": building, "apartments": apts}
            for building, apts in vacant_by_building.items()
        ]

        # Condominium income = total - all owner incomes
        owner_total = Decimal("0.00")
        for info in owner_income_map.values():
            owner_total += info["total"]
        condominium_income = total_income - owner_total

        # Count condominium kitnets (rented, no owner)
        condominium_count = Apartment.objects.filter(is_rented=True, owner__isnull=True).count()

        extra_income_total, extra_incomes = FinancialDashboardService._collect_extra_incomes(
            month_start
        )

        return {
            "total_monthly_income": total_income,
            "all_apartments": all_apartments,
            "owner_incomes": list(owner_income_map.values()),
            "owner_total": owner_total,
            "vacant_kitnets": vacant_list,
            "vacant_by_building": vacant_by_building_list,
            "vacant_count": len(vacant_list),
            "vacant_lost_rent": vacant_lost_rent,
            "condominium_income": condominium_income,
            "condominium_kitnet_count": condominium_count,
            "salary_offset_total": salary_offset_total,
            "salary_offset_apartments": salary_offset_apartments,
            "extra_incomes": extra_incomes,
            "extra_income_total": extra_income_total,
        }

    @staticmethod
    def _collect_extra_incomes(
        month_start: date,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Collect recurring and one-time extra incomes for the month."""
        next_month = _next_month_start(month_start.year, month_start.month)
        extra_incomes: list[dict[str, Any]] = []
        extra_income_total = Decimal("0.00")

        for inc in Income.objects.filter(
            is_recurring=True, expected_monthly_amount__isnull=False
        ).select_related("person"):
            amount = inc.expected_monthly_amount or Decimal("0.00")
            extra_income_total += amount
            extra_incomes.append(
                {
                    "description": inc.description,
                    "amount": amount,
                    "is_recurring": True,
                    "person_name": inc.person.name if inc.person else None,
                }
            )

        for inc in Income.objects.filter(
            income_date__gte=month_start,
            income_date__lt=next_month,
            is_recurring=False,
        ).select_related("person"):
            extra_income_total += inc.amount
            extra_incomes.append(
                {
                    "description": inc.description,
                    "amount": inc.amount,
                    "is_recurring": False,
                    "person_name": inc.person.name if inc.person else None,
                }
            )

        return extra_income_total, extra_incomes

    @staticmethod
    @staticmethod
    def _ensure_employee_payments(month_start: date) -> None:
        """Auto-create EmployeePayment for employees missing one this month.

        Uses the most recent payment's base_salary as default.
        Only creates with base_salary; variable_amount stays 0 for manual adjustment.
        """
        employees = Person.objects.filter(is_employee=True)
        for employee in employees:
            if EmployeePayment.objects.filter(
                person=employee, reference_month=month_start
            ).exists():
                continue
            last_payment = (
                EmployeePayment.objects.filter(person=employee).order_by("-reference_month").first()
            )
            if last_payment is None:
                continue
            EmployeePayment.objects.create(
                person=employee,
                reference_month=month_start,
                base_salary=last_payment.base_salary,
                variable_amount=Decimal("0.00"),
            )

    @staticmethod
    def _build_expense_summary(
        month_start: date,
        next_month: date,
        year: int,
        month: int,
        skipped_expense_ids: set[int],
    ) -> dict[str, Any]:
        """Build expense breakdown: per person, utility bills, IPTU."""
        # Per-person expense summary with waterfall payment allocation
        persons = Person.objects.filter(is_employee=False).order_by("name")
        person_expenses: list[dict[str, Any]] = []
        current_key = f"{year}-{month:02d}"

        for person in persons:
            person_data = FinancialDashboardService._get_person_month_expenses(
                person, month_start, next_month, skipped_expense_ids
            )
            # Use waterfall for payable persons to get correct allocated payment
            if person_data["is_payable"]:
                waterfall = FinancialDashboardService._get_person_waterfall(person, year, month)
                current_alloc = waterfall.get(current_key)
                if current_alloc:
                    person_data["total_paid"] = current_alloc["allocated_paid"]
                    person_data["pending"] = current_alloc["pending"]

            if person_data["total"] > 0:
                person_expenses.append(person_data)

        # Utility bills grouped by building
        water_data = FinancialDashboardService._build_utility_by_building(
            ExpenseType.WATER_BILL, month_start, next_month
        )
        electricity_data = FinancialDashboardService._build_utility_by_building(
            ExpenseType.ELECTRICITY_BILL, month_start, next_month
        )

        # IPTU installments grouped by building
        iptu_installments = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__expense_type=ExpenseType.PROPERTY_TAX,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .select_related("expense", "expense__building")
        )

        iptu_total = Decimal("0.00")
        iptu_by_building: dict[str, dict[str, Any]] = {}
        for inst in iptu_installments:
            building_name = (
                str(inst.expense.building.street_number) if inst.expense.building else "Outros"
            )
            if building_name not in iptu_by_building:
                iptu_by_building[building_name] = {
                    "building_name": building_name,
                    "bills": [],
                    "debt_installments": [],
                    "bill_total": Decimal("0.00"),
                    "debt_total": Decimal("0.00"),
                    "total": Decimal("0.00"),
                }
            entry = iptu_by_building[building_name]
            entry["bills"].append(
                {
                    "description": inst.expense.description,
                    "amount": inst.amount,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                }
            )
            entry["bill_total"] += inst.amount
            entry["total"] += inst.amount
            iptu_total += inst.amount

        iptu_data = {
            "total": iptu_total,
            "by_building": sorted(iptu_by_building.values(), key=lambda x: x["building_name"]),
        }

        # Categorized fixed expenses (not already assigned to a person)
        fixed_categories = FinancialDashboardService._build_fixed_expense_categories(
            month_start, skipped_expense_ids
        )

        # Employee salary payments for this month + salary offset rents
        # Auto-create missing payments for employees based on previous month
        FinancialDashboardService._ensure_employee_payments(month_start)
        employee_payments = EmployeePayment.objects.filter(
            reference_month=month_start,
        ).select_related("person")
        employee_total = Decimal("0.00")
        employee_details: list[dict[str, Any]] = []
        for payment in employee_payments:
            amount = payment.total_paid
            employee_total += amount
            employee_details.append(
                {
                    "employee_payment_id": payment.pk,
                    "person_name": payment.person.name,
                    "description": f"{payment.person.name} — Salário",
                    "amount": amount,
                    "base_salary": payment.base_salary,
                    "variable_amount": payment.variable_amount,
                    "notes": payment.notes,
                    "is_paid": payment.is_paid,
                    "breakdown": f"Base R${payment.base_salary}"
                    + (
                        f" + Variável R${payment.variable_amount}"
                        if payment.variable_amount
                        else ""
                    ),
                }
            )

        # Add salary offset apartment rents as employee cost
        salary_offset_leases = Lease.objects.filter(
            apartment__is_rented=True,
            is_salary_offset=True,
        ).select_related("apartment", "apartment__building", "responsible_tenant")
        for lease in salary_offset_leases:
            employee_total += lease.rental_value
            apt_label = f"{lease.apartment.number}/{lease.apartment.building.street_number}"
            employee_details.append(
                {
                    "employee_payment_id": None,
                    "description": f"{lease.responsible_tenant.name} — Aluguel Apto {apt_label}",
                    "amount": lease.rental_value,
                    "notes": "Compensação salarial (aluguel não gera receita)",
                    "is_salary_offset": True,
                }
            )

        all_totals = (
            sum((p["total"] for p in person_expenses), Decimal("0.00"))
            + water_data["total"]
            + electricity_data["total"]
            + iptu_data["total"]
            + fixed_categories["internet"]["total"]
            + fixed_categories["celular"]["total"]
            + fixed_categories["sitio"]["total"]
            + fixed_categories["outros_fixed"]["total"]
            + employee_total
        )

        return {
            "by_person": person_expenses,
            "water": water_data,
            "electricity": electricity_data,
            "iptu": iptu_data,
            "employee": {"total": employee_total, "details": employee_details},
            **fixed_categories,
            "total": all_totals,
        }

    @staticmethod
    def _build_fixed_expense_categories(
        month_start: date,
        skipped_expense_ids: set[int],
    ) -> dict[str, dict[str, Any]]:
        """Categorize fixed expenses + orphan one-time expenses into internet, celular, sítio, and outros."""
        next_month = month_start.replace(day=28) + timedelta(days=4)
        next_month = next_month.replace(day=1)

        fixed_expenses = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                is_offset=False,
                person__isnull=True,
            )
            .exclude(end_date__lt=month_start)
            .exclude(pk__in=skipped_expense_ids)
        )

        # One-time expenses without a person (not captured elsewhere)
        orphan_one_time = Expense.objects.filter(
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            is_offset=False,
            person__isnull=True,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).exclude(pk__in=skipped_expense_ids)

        internet: list[dict[str, Any]] = []
        internet_total = Decimal("0.00")
        celular: list[dict[str, Any]] = []
        celular_total = Decimal("0.00")
        sitio: list[dict[str, Any]] = []
        sitio_total = Decimal("0.00")
        outros: list[dict[str, Any]] = []
        outros_total = Decimal("0.00")

        for exp in fixed_expenses:
            amount = exp.expected_monthly_amount or exp.total_amount
            item = {"description": exp.description, "amount": amount}
            desc_lower = exp.description.lower()

            if "internet" in desc_lower:
                internet.append(item)
                internet_total += amount
            elif "claro" in desc_lower:
                celular.append(item)
                celular_total += amount
            elif "sítio" in desc_lower or "sitio" in desc_lower or "ração" in desc_lower:
                sitio.append(item)
                sitio_total += amount
            else:
                outros.append(item)
                outros_total += amount

        for exp in orphan_one_time:
            amount = exp.total_amount
            outros.append({"description": exp.description, "amount": amount})
            outros_total += amount

        return {
            "internet": {"total": internet_total, "details": internet},
            "celular": {"total": celular_total, "details": celular},
            "sitio": {"total": sitio_total, "details": sitio},
            "outros_fixed": {"total": outros_total, "details": outros},
        }

    @staticmethod
    def _build_utility_by_building(
        expense_type: str, month_start: date, next_month: date
    ) -> dict[str, Any]:
        """Build utility bill data grouped by building, with debt installments as sub-items."""
        # Monthly bills (not debt installments, not already paid): specific month + recurring
        bills = (
            Expense.objects.filter(
                expense_type=expense_type,
                is_debt_installment=False,
                is_offset=False,
                is_paid=False,
            )
            .filter(
                Q(expense_date__gte=month_start, expense_date__lt=next_month)
                | Q(is_recurring=True, expected_monthly_amount__isnull=False),
            )
            .exclude(
                end_date__lt=month_start,
            )
            .select_related("building")
        )

        # Debt installments for this utility type
        debt_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__expense_type=expense_type,
            expense__is_debt_installment=True,
        ).select_related("expense", "expense__building")

        # Index debt installments by building name
        debt_by_building: dict[str, list[dict[str, Any]]] = {}
        for inst in debt_installments:
            building_name = _resolve_building_label(inst.expense.building, inst.expense.description)
            if building_name not in debt_by_building:
                debt_by_building[building_name] = []
            debt_by_building[building_name].append(
                {
                    "expense_id": inst.expense_id,
                    "installment_id": inst.pk,
                    "description": inst.expense.description,
                    "amount": inst.amount,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "installment_number": inst.installment_number,
                    "total_installments": inst.total_installments,
                }
            )

        # Group bills by building, merging debt info
        buildings_map: dict[str, dict[str, Any]] = {}
        grand_total = Decimal("0.00")

        for bill in bills:
            building_name = _resolve_building_label(bill.building, bill.description)
            if building_name not in buildings_map:
                buildings_map[building_name] = {
                    "building_name": building_name,
                    "bills": [],
                    "debt_installments": [],
                    "bill_total": Decimal("0.00"),
                    "debt_total": Decimal("0.00"),
                    "total": Decimal("0.00"),
                }
            amount = (
                bill.expected_monthly_amount
                if bill.is_recurring and bill.expected_monthly_amount
                else bill.total_amount
            )
            buildings_map[building_name]["bills"].append(
                {
                    "expense_id": bill.pk,
                    "installment_id": None,
                    "description": bill.description,
                    "amount": amount,
                }
            )
            buildings_map[building_name]["bill_total"] += amount
            buildings_map[building_name]["total"] += amount
            grand_total += amount

        # Merge debt installments into their buildings (or create new entry)
        for building_name, debts in debt_by_building.items():
            if building_name not in buildings_map:
                buildings_map[building_name] = {
                    "building_name": building_name,
                    "bills": [],
                    "debt_installments": [],
                    "bill_total": Decimal("0.00"),
                    "debt_total": Decimal("0.00"),
                    "total": Decimal("0.00"),
                }
            entry = buildings_map[building_name]
            for debt in debts:
                entry["debt_installments"].append(debt)
                debt_amount = debt["amount"]
                entry["debt_total"] += debt_amount
                # Debt is already included in the bill total, so don't add to total
                # But if there's no bill for this building, it's standalone debt
                if not entry["bills"]:
                    entry["total"] += debt_amount
                    grand_total += debt_amount

        # Add notes about future debt and missing bills
        FinancialDashboardService._add_utility_notes(buildings_map, expense_type, next_month)

        by_building = sorted(buildings_map.values(), key=lambda x: x["building_name"])

        return {
            "total": grand_total,
            "by_building": by_building,
        }

    @staticmethod
    def _add_utility_notes(
        buildings_map: dict[str, dict[str, Any]],
        expense_type: str,
        next_month: date,
    ) -> None:
        """Add notes about truly new debt installments (not yet started) and missing bills."""
        for building in Building.objects.all():
            building_name = str(building.street_number)

            # Only show note for debts where the FIRST installment is in the future
            # (i.e., parcelamento that hasn't started yet — not ongoing ones)
            first_installment = (
                ExpenseInstallment.objects.filter(
                    expense__expense_type=expense_type,
                    expense__is_debt_installment=True,
                    expense__building=building,
                    installment_number=1,
                    is_paid=False,
                    due_date__gte=next_month,
                )
                .select_related("expense")
                .first()
            )

            if first_installment:
                amount_fmt = (
                    f"{first_installment.amount:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                start_date = first_installment.due_date.strftime("%m/%Y")
                total_inst = first_installment.expense.total_installments
                note = f"Parcelamento inicia em {start_date}: {total_inst}x de R$ {amount_fmt}"

                if building_name not in buildings_map:
                    buildings_map[building_name] = {
                        "building_name": building_name,
                        "bills": [],
                        "debt_installments": [],
                        "bill_total": Decimal("0.00"),
                        "debt_total": Decimal("0.00"),
                        "total": Decimal("0.00"),
                        "notes": [note],
                    }
                else:
                    buildings_map[building_name].setdefault("notes", []).append(note)

            # Note for buildings with no bill and no debt this month
            entry = buildings_map.get(building_name)
            if entry and not entry["bills"] and not entry["debt_installments"]:
                entry.setdefault("notes", []).insert(0, "Aguardando parcelamento da conta")

        # Ensure all entries have 'notes' key
        for entry in buildings_map.values():
            entry.setdefault("notes", [])

    @staticmethod
    def _get_person_month_expenses(
        person: Person,
        month_start: date,
        next_month: date,
        skipped_expense_ids: set[int],
    ) -> dict[str, Any]:
        """Get a person's expense summary for a given month (cards, loans, fixed, one-time, offsets)."""
        # Card purchases — installment-based
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
        card_details: list[dict[str, Any]] = []
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
                }
            )

        # Card purchases — single payment (faturas, not installment-based)
        card_single = (
            Expense.objects.filter(
                expense_type=ExpenseType.CARD_PURCHASE,
                person=person,
                is_installment=False,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            )
            .exclude(pk__in=skipped_expense_ids)
            .select_related("credit_card")
        )
        for exp in card_single:
            card_total += exp.total_amount
            card_details.append(
                {
                    "description": exp.description,
                    "card_name": exp.credit_card.nickname if exp.credit_card else None,
                    "amount": exp.total_amount,
                }
            )

        # Loan installments (bank + personal loans)
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
        loan_details: list[dict[str, Any]] = []
        for inst in loan_installments:
            loan_total += inst.amount
            loan_details.append(
                {
                    "description": inst.expense.description,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                }
            )

        # Loan single payments (not installment-based)
        loan_single = Expense.objects.filter(
            expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
            person=person,
            is_installment=False,
            is_offset=False,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).exclude(pk__in=skipped_expense_ids)
        for exp in loan_single:
            loan_total += exp.total_amount
            loan_details.append({"description": exp.description, "amount": exp.total_amount})

        # Fixed recurring expenses for this person
        fixed_expenses = (
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
        fixed_details: list[dict[str, Any]] = []
        for exp in fixed_expenses:
            amount = exp.expected_monthly_amount or exp.total_amount
            fixed_total += amount
            fixed_details.append({"description": exp.description, "amount": amount})

        # One-time expenses for this person in the month
        one_time_expenses = Expense.objects.filter(
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            person=person,
            is_offset=False,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).exclude(pk__in=skipped_expense_ids)
        one_time_total = Decimal("0.00")
        one_time_details: list[dict[str, Any]] = []
        for exp in one_time_expenses:
            one_time_total += exp.total_amount
            one_time_details.append({"description": exp.description, "amount": exp.total_amount})

        # Offset/discount installments (purchases on this person's card for others)
        offset_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__person=person,
            expense__is_offset=True,
        ).select_related("expense", "expense__credit_card")
        # Also non-installment offset expenses
        offset_single = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=next_month,
            person=person,
            is_offset=True,
            is_installment=False,
        )
        offset_total = Decimal("0.00")
        offset_details: list[dict[str, Any]] = []
        for inst in offset_installments:
            offset_total += inst.amount
            offset_details.append(
                {
                    "description": inst.expense.description,
                    "card_name": inst.expense.credit_card.nickname
                    if inst.expense.credit_card
                    else None,
                    "installment": f"{inst.installment_number}/{inst.total_installments}",
                    "amount": inst.amount,
                }
            )
        for exp in offset_single:
            offset_total += exp.total_amount
            offset_details.append({"description": exp.description, "amount": exp.total_amount})

        # Fixed stipends for this person
        stipends = PersonIncome.objects.filter(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
            start_date__lte=month_start,
        ).exclude(end_date__lt=month_start)
        stipend_total = Decimal("0.00")
        stipend_details: list[dict[str, Any]] = []
        for stipend in stipends:
            amount = stipend.fixed_amount or Decimal("0.00")
            stipend_total += amount
            stipend_details.append({"description": "Estipêndio fixo", "amount": amount})

        total_expenses = (
            card_total + loan_total + fixed_total + one_time_total + stipend_total - offset_total
        )

        # Payments made to this person for this month
        total_paid = PersonPayment.objects.filter(
            person=person,
            reference_month=month_start,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        return {
            "person_id": person.pk,
            "person_name": person.name,
            "card_total": card_total,
            "card_details": card_details,
            "loan_total": loan_total,
            "loan_details": loan_details,
            "fixed_total": fixed_total,
            "fixed_details": fixed_details,
            "one_time_total": one_time_total,
            "one_time_details": one_time_details,
            "offset_total": offset_total,
            "offset_details": offset_details,
            "stipend_total": stipend_total,
            "stipend_details": stipend_details,
            "total": total_expenses,
            "total_paid": total_paid,
            "pending": total_expenses - total_paid,
            "is_payable": PersonIncome.objects.filter(person=person, is_active=True).exists()
            or Apartment.objects.filter(owner=person).exists(),
        }

    @staticmethod
    def _resolve_category_fields(
        category: Any,
    ) -> tuple[int | None, str | None, str | None, int | None, str | None]:
        """Resolve category/subcategory fields from an ExpenseCategory instance.

        Returns (category_id, category_name, category_color, subcategory_id, subcategory_name).
        If the category has a parent, the parent is the top-level category and the
        category itself is the subcategory.
        """
        if category is None:
            return None, None, None, None, None
        if category.parent_id is not None:
            return (
                category.parent.id,
                category.parent.name,
                category.parent.color,
                category.id,
                category.name,
            )
        return category.id, category.name, category.color, None, None

    @staticmethod
    def _enriched_installment_item(inst: Any) -> dict[str, Any]:
        """Build enriched detail item from an ExpenseInstallment."""
        cat_id, cat_name, cat_color, sub_id, sub_name = (
            FinancialDashboardService._resolve_category_fields(inst.expense.category)
        )
        return {
            "expense_id": inst.expense.id,
            "installment_id": inst.id,
            "description": inst.expense.description,
            "card_name": getattr(inst.expense.credit_card, "nickname", None)
            if inst.expense.credit_card
            else None,
            "installment_number": inst.installment_number,
            "total_installments": inst.total_installments,
            "category_id": cat_id,
            "category_name": cat_name,
            "category_color": cat_color,
            "subcategory_id": sub_id,
            "subcategory_name": sub_name,
            "notes": inst.expense.notes,
            "amount": inst.amount,
            "due_date": inst.due_date.isoformat(),
        }

    @staticmethod
    def _collect_overdue_installments(
        expense_type: str,
        month_start: date,
    ) -> list[dict[str, Any]]:
        """Collect unpaid installments with due_date before month_start for a given expense type."""
        today = timezone.now().date()
        overdue_qs = (
            ExpenseInstallment.objects.filter(
                due_date__lt=month_start,
                is_paid=False,
                expense__expense_type=expense_type,
                expense__is_offset=False,
            )
            .select_related(
                "expense",
                "expense__building",
                "expense__category",
                "expense__category__parent",
                "expense__credit_card",
            )
            .order_by("due_date")
        )
        items = []
        for inst in overdue_qs:
            item = FinancialDashboardService._enriched_installment_item(inst)
            item["days_overdue"] = (today - inst.due_date).days
            item["is_paid"] = False
            building = inst.expense.building
            item["building_name"] = str(building.street_number) if building else None
            items.append(item)
        return items

    @staticmethod
    def _enriched_expense_item(exp: Any) -> dict[str, Any]:
        """Build enriched detail item from a single Expense (no installment)."""
        cat_id, cat_name, cat_color, sub_id, sub_name = (
            FinancialDashboardService._resolve_category_fields(exp.category)
        )
        return {
            "expense_id": exp.id,
            "installment_id": None,
            "description": exp.description,
            "card_name": getattr(exp.credit_card, "nickname", None) if exp.credit_card else None,
            "installment_number": None,
            "total_installments": None,
            "category_id": cat_id,
            "category_name": cat_name,
            "category_color": cat_color,
            "subcategory_id": sub_id,
            "subcategory_name": sub_name,
            "notes": exp.notes,
            "amount": exp.total_amount,
            "due_date": exp.expense_date.isoformat() if exp.expense_date else None,
        }

    @staticmethod
    def _get_person_expense_detail(
        person: Person, month_start: date, next_month: date
    ) -> dict[str, Any]:
        """Get enriched expense detail for a person with full category/notes/id info."""
        enrich_inst = FinancialDashboardService._enriched_installment_item
        enrich_exp = FinancialDashboardService._enriched_expense_item
        sel_inst = [
            "expense",
            "expense__credit_card",
            "expense__category",
            "expense__category__parent",
        ]
        sel_exp = ["credit_card", "category", "category__parent"]

        def collect_installments(qs: Any) -> tuple[Decimal, list[dict[str, Any]]]:
            total = Decimal("0.00")
            details: list[dict[str, Any]] = []
            for inst in qs:
                total += inst.amount
                details.append(enrich_inst(inst))
            return total, details

        def collect_single(qs: Any) -> tuple[Decimal, list[dict[str, Any]]]:
            total = Decimal("0.00")
            details: list[dict[str, Any]] = []
            for exp in qs:
                total += exp.total_amount
                details.append(enrich_exp(exp))
            return total, details

        # Card purchases
        card_total, card_details = collect_installments(
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__expense_type=ExpenseType.CARD_PURCHASE,
                expense__is_debt_installment=False,
                expense__is_offset=False,
            ).select_related(*sel_inst)
        )
        single_total, single_details = collect_single(
            Expense.objects.filter(
                expense_type=ExpenseType.CARD_PURCHASE,
                person=person,
                is_installment=False,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            ).select_related(*sel_exp)
        )
        card_total += single_total
        card_details.extend(single_details)

        loan_types = [ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN]
        loan_total, loan_details = collect_installments(
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__expense_type__in=loan_types,
                expense__is_offset=False,
            ).select_related(*sel_inst)
        )
        single_total, single_details = collect_single(
            Expense.objects.filter(
                expense_type__in=loan_types,
                person=person,
                is_installment=False,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            ).select_related(*sel_exp)
        )
        loan_total += single_total
        loan_details.extend(single_details)

        # Fixed recurring expenses
        fixed_total = Decimal("0.00")
        fixed_details: list[dict[str, Any]] = []
        for exp in (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                person=person,
                is_offset=False,
            )
            .exclude(end_date__lt=month_start)
            .select_related(*sel_exp)
        ):
            amount = exp.expected_monthly_amount or exp.total_amount
            item = enrich_exp(exp)
            item["amount"] = amount
            item["due_date"] = None
            fixed_total += amount
            fixed_details.append(item)

        # One-time expenses
        one_time_total, one_time_details = collect_single(
            Expense.objects.filter(
                expense_type=ExpenseType.ONE_TIME_EXPENSE,
                person=person,
                is_offset=False,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
            ).select_related(*sel_exp)
        )

        # Offsets
        offset_total, offset_details = collect_installments(
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__person=person,
                expense__is_offset=True,
            ).select_related(*sel_inst)
        )
        single_total, single_details = collect_single(
            Expense.objects.filter(
                expense_date__gte=month_start,
                expense_date__lt=next_month,
                person=person,
                is_offset=True,
                is_installment=False,
            ).select_related(*sel_exp)
        )
        offset_total += single_total
        offset_details.extend(single_details)

        # Stipends
        stipend_total = Decimal("0.00")
        stipend_details: list[dict[str, Any]] = []
        for stipend in PersonIncome.objects.filter(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
            start_date__lte=month_start,
        ).exclude(end_date__lt=month_start):
            amount = stipend.fixed_amount or Decimal("0.00")
            stipend_total += amount
            stipend_details.append(
                {
                    "expense_id": None,
                    "installment_id": None,
                    "description": "Estipêndio fixo",
                    "card_name": None,
                    "installment_number": None,
                    "total_installments": None,
                    "category_id": None,
                    "category_name": None,
                    "category_color": None,
                    "subcategory_id": None,
                    "subcategory_name": None,
                    "notes": None,
                    "amount": amount,
                    "due_date": None,
                }
            )

        total_expenses = (
            card_total + loan_total + fixed_total + one_time_total + stipend_total - offset_total
        )

        return {
            "card_total": card_total,
            "card_details": card_details,
            "loan_total": loan_total,
            "loan_details": loan_details,
            "fixed_total": fixed_total,
            "fixed_details": fixed_details,
            "one_time_total": one_time_total,
            "one_time_details": one_time_details,
            "offset_total": offset_total,
            "offset_details": offset_details,
            "stipend_total": stipend_total,
            "stipend_details": stipend_details,
            "total": total_expenses,
        }

    @staticmethod
    def get_expense_detail(
        detail_type: str, detail_id: int | None, year: int, month: int
    ) -> dict[str, Any]:
        """Return full expense breakdown for a specific category and month.

        detail_type options:
          "person"       — requires detail_id = Person PK
          "electricity"  — utility bills grouped by building
          "water"        — utility bills grouped by building
          "iptu"         — property tax installments grouped by building
          "internet"     — fixed expense category
          "celular"      — fixed expense category
          "sitio"        — fixed expense category
          "outros_fixed" — fixed expense category
          "employee"     — employee salary payments
        """
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        dispatch: dict[str, Callable[[], dict[str, Any]]] = {
            "person": lambda: FinancialDashboardService._detail_person(
                detail_id, year, month, month_start, next_month
            ),
            "electricity": lambda: FinancialDashboardService._detail_utility(
                "electricity",
                ExpenseType.ELECTRICITY_BILL,
                "Contas de Luz",
                month_start,
                next_month,
            ),
            "water": lambda: FinancialDashboardService._detail_utility(
                "water", ExpenseType.WATER_BILL, "Contas de Água", month_start, next_month
            ),
            "iptu": lambda: FinancialDashboardService._detail_iptu(month_start, next_month),
            "employee": lambda: FinancialDashboardService._detail_employee(month_start),
        }
        fixed_label_map = {
            "internet": "Internet",
            "celular": "Celular",
            "sitio": "Sítio",
            "outros_fixed": "Outros Fixos",
        }
        if detail_type in fixed_label_map:
            return FinancialDashboardService._detail_fixed_category(
                detail_type, fixed_label_map[detail_type], month_start
            )
        handler = dispatch.get(detail_type)
        if handler is None:
            return {"error": f"Unknown detail_type: {detail_type}"}
        return handler()

    @staticmethod
    def _detail_person(
        detail_id: int | None,
        year: int,
        month: int,
        month_start: date,
        next_month: date,
    ) -> dict[str, Any]:
        """Return enriched expense detail for a single person with waterfall allocation."""
        if detail_id is None:
            return {"error": "detail_id is required for type=person"}
        try:
            person = Person.objects.get(pk=detail_id)
        except Person.DoesNotExist:
            return {"error": f"Person {detail_id} not found"}

        detail = FinancialDashboardService._get_person_expense_detail(
            person, month_start, next_month
        )
        is_payable = (
            PersonIncome.objects.filter(person=person, is_active=True).exists()
            or Apartment.objects.filter(owner=person).exists()
        )
        total_paid: Decimal = detail["total"]
        pending = Decimal("0.00")
        if is_payable:
            current_key = f"{year}-{month:02d}"
            waterfall = FinancialDashboardService._get_person_waterfall(person, year, month)
            current_alloc = waterfall.get(current_key)
            if current_alloc:
                total_paid = current_alloc["allocated_paid"]
                pending = current_alloc["pending"]

        return {
            "detail_type": "person",
            "person_id": person.pk,
            "person_name": person.name,
            "is_payable": is_payable,
            **detail,
            "total_paid": total_paid,
            "pending": pending,
        }

    @staticmethod
    def _detail_utility(
        detail_type: str,
        expense_type: str,
        label: str,
        month_start: date,
        next_month: date,
    ) -> dict[str, Any]:
        """Return utility bill detail grouped by building."""
        utility_data = FinancialDashboardService._build_utility_by_building(
            expense_type, month_start, next_month
        )
        overdue = FinancialDashboardService._collect_overdue_installments(expense_type, month_start)
        return {
            "detail_type": detail_type,
            "label": label,
            **utility_data,
            "overdue": overdue,
            "overdue_total": sum(item["amount"] for item in overdue),
        }

    @staticmethod
    def _detail_iptu(month_start: date, next_month: date) -> dict[str, Any]:
        """Return IPTU installment detail grouped by building with enriched items."""
        iptu_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__expense_type=ExpenseType.PROPERTY_TAX,
        ).select_related(
            "expense",
            "expense__building",
            "expense__category",
            "expense__category__parent",
        )
        iptu_total = Decimal("0.00")
        iptu_by_building: dict[str, dict[str, Any]] = {}
        for inst in iptu_installments:
            building_name = (
                str(inst.expense.building.street_number) if inst.expense.building else "Outros"
            )
            if building_name not in iptu_by_building:
                iptu_by_building[building_name] = {
                    "building_name": building_name,
                    "bills": [],
                    "bill_total": Decimal("0.00"),
                    "total": Decimal("0.00"),
                }
            entry = iptu_by_building[building_name]
            entry["bills"].append(FinancialDashboardService._enriched_installment_item(inst))
            entry["bill_total"] += inst.amount
            entry["total"] += inst.amount
            iptu_total += inst.amount

        overdue = FinancialDashboardService._collect_overdue_installments(
            ExpenseType.PROPERTY_TAX, month_start
        )

        return {
            "detail_type": "iptu",
            "label": "IPTU",
            "total": iptu_total,
            "by_building": sorted(iptu_by_building.values(), key=lambda x: x["building_name"]),
            "overdue": overdue,
            "overdue_total": sum(item["amount"] for item in overdue),
        }

    @staticmethod
    def _detail_fixed_category(detail_type: str, label: str, month_start: date) -> dict[str, Any]:
        """Return enriched detail for a single fixed expense category."""
        fixed_categories = FinancialDashboardService._build_fixed_expense_categories_detail(
            month_start
        )
        category_data = fixed_categories.get(detail_type, {"total": Decimal("0.00"), "details": []})
        return {"detail_type": detail_type, "label": label, **category_data}

    @staticmethod
    def _detail_employee(month_start: date) -> dict[str, Any]:
        """Return employee salary payment detail + salary offset rents for the month."""
        FinancialDashboardService._ensure_employee_payments(month_start)

        employee_total = Decimal("0.00")
        employee_details: list[dict[str, Any]] = []

        # Salary payments
        for payment in EmployeePayment.objects.filter(
            reference_month=month_start,
        ).select_related("person"):
            amount = payment.total_paid
            employee_total += amount
            employee_details.append(
                {
                    "expense_id": None,
                    "installment_id": None,
                    "employee_payment_id": payment.pk,
                    "person_name": payment.person.name,
                    "description": f"{payment.person.name} — Salário",
                    "amount": amount,
                    "base_salary": payment.base_salary,
                    "variable_amount": payment.variable_amount,
                    "is_paid": payment.is_paid,
                    "notes": f"Base R${payment.base_salary}"
                    + (
                        f" + Variável R${payment.variable_amount}"
                        if payment.variable_amount
                        else ""
                    ),
                    "category_name": None,
                    "category_color": None,
                    "installment_number": None,
                    "total_installments": None,
                }
            )

        # Salary offset apartment rents (employee housing compensation)
        for lease in Lease.objects.filter(
            apartment__is_rented=True,
            is_salary_offset=True,
        ).select_related("apartment", "apartment__building", "responsible_tenant"):
            employee_total += lease.rental_value
            apt_label = f"{lease.apartment.number}/{lease.apartment.building.street_number}"
            employee_details.append(
                {
                    "expense_id": None,
                    "installment_id": None,
                    "description": f"{lease.responsible_tenant.name} — Aluguel Apto {apt_label}",
                    "amount": lease.rental_value,
                    "notes": "Compensação salarial (aluguel não gera receita)",
                    "category_name": None,
                    "category_color": None,
                    "installment_number": None,
                    "total_installments": None,
                }
            )

        return {
            "detail_type": "employee",
            "label": "Funcionários",
            "total": employee_total,
            "details": employee_details,
        }

    @staticmethod
    def get_monthly_purchases(year: int, month: int) -> dict[str, Any]:
        """Return new purchases/expenses introduced in the given month.

        Groups items into: card_purchases, loans, utility_bills, one_time_expenses,
        fixed_expenses. Also returns aggregation by category with percentages.
        """
        month_start = date(year, month, 1)
        next_month = _next_month_start(year, month)

        skipped_expense_ids: set[int] = set(
            ExpenseMonthSkip.objects.filter(
                reference_month=month_start,
            ).values_list("expense_id", flat=True)
        )

        sel_inst = [
            "expense",
            "expense__person",
            "expense__credit_card",
            "expense__category",
            "expense__category__parent",
        ]
        sel_exp = ["person", "credit_card", "category", "category__parent"]

        # 1. Card purchases — first installment only, due this month
        card_installments = (
            ExpenseInstallment.objects.filter(
                installment_number=1,
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__expense_type=ExpenseType.CARD_PURCHASE,
                expense__is_offset=False,
                expense__is_debt_installment=False,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .select_related(*sel_inst)
        )
        card_items = [
            FinancialDashboardService._purchase_item_from_installment(inst)
            for inst in card_installments
        ]
        card_total = sum((item["amount"] for item in card_items), Decimal("0.00"))

        # 2. Loans — first installment only, due this month
        loan_installments = (
            ExpenseInstallment.objects.filter(
                installment_number=1,
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__expense_type__in=[ExpenseType.BANK_LOAN, ExpenseType.PERSONAL_LOAN],
                expense__is_offset=False,
                expense__is_debt_installment=False,
            )
            .exclude(expense_id__in=skipped_expense_ids)
            .select_related(*sel_inst)
        )
        loan_items = [
            FinancialDashboardService._purchase_item_from_installment(inst)
            for inst in loan_installments
        ]
        loan_total = sum((item["amount"] for item in loan_items), Decimal("0.00"))

        # 3. Utility bills — expense_date falls in this month
        utility_expenses = (
            Expense.objects.filter(
                expense_type__in=[ExpenseType.WATER_BILL, ExpenseType.ELECTRICITY_BILL],
                expense_date__gte=month_start,
                expense_date__lt=next_month,
                is_offset=False,
            )
            .exclude(pk__in=skipped_expense_ids)
            .select_related(*sel_exp)
        )
        utility_items = [
            FinancialDashboardService._purchase_item_from_expense(exp) for exp in utility_expenses
        ]
        utility_total = sum((item["amount"] for item in utility_items), Decimal("0.00"))

        # 4. One-time expenses — expense_date falls in this month
        one_time_expenses = (
            Expense.objects.filter(
                expense_type=ExpenseType.ONE_TIME_EXPENSE,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
                is_offset=False,
            )
            .exclude(pk__in=skipped_expense_ids)
            .select_related(*sel_exp)
        )
        one_time_items = [
            FinancialDashboardService._purchase_item_from_expense(exp) for exp in one_time_expenses
        ]
        one_time_total = sum((item["amount"] for item in one_time_items), Decimal("0.00"))

        # 5. Fixed recurring — active this month (end_date null or >= month_start)
        fixed_expenses = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                expected_monthly_amount__isnull=False,
                is_offset=False,
            )
            .exclude(end_date__lt=month_start)
            .exclude(pk__in=skipped_expense_ids)
            .select_related(*sel_exp)
        )
        fixed_items = [
            FinancialDashboardService._purchase_item_from_expense(exp, use_expected_amount=True)
            for exp in fixed_expenses
        ]
        fixed_total = sum((item["amount"] for item in fixed_items), Decimal("0.00"))

        grand_total = card_total + loan_total + utility_total + one_time_total + fixed_total

        by_category = FinancialDashboardService._aggregate_purchases_by_category(
            card_items + loan_items + utility_items + one_time_items + fixed_items,
            grand_total,
        )

        return {
            "year": year,
            "month": month,
            "total": grand_total,
            "by_type": {
                "card_purchases": {
                    "total": card_total,
                    "count": len(card_items),
                    "items": card_items,
                },
                "loans": {
                    "total": loan_total,
                    "count": len(loan_items),
                    "items": loan_items,
                },
                "utility_bills": {
                    "total": utility_total,
                    "count": len(utility_items),
                    "items": utility_items,
                },
                "one_time_expenses": {
                    "total": one_time_total,
                    "count": len(one_time_items),
                    "items": one_time_items,
                },
                "fixed_expenses": {
                    "total": fixed_total,
                    "count": len(fixed_items),
                    "items": fixed_items,
                },
            },
            "by_category": by_category,
        }

    @staticmethod
    def _purchase_item_from_installment(inst: Any) -> dict[str, Any]:
        """Build a purchase item dict from an ExpenseInstallment."""
        cat_id, cat_name, cat_color, _sub_id, _sub_name = (
            FinancialDashboardService._resolve_category_fields(inst.expense.category)
        )
        return {
            "description": inst.expense.description,
            "amount": inst.amount,
            "total_amount": inst.expense.total_amount,
            "total_installments": inst.total_installments,
            "person_name": inst.expense.person.name if inst.expense.person else None,
            "card_name": inst.expense.credit_card.nickname if inst.expense.credit_card else None,
            "category_id": cat_id,
            "category_name": cat_name,
            "category_color": cat_color,
            "date": inst.due_date.isoformat(),
            "expense_type": inst.expense.expense_type,
        }

    @staticmethod
    def _purchase_item_from_expense(
        exp: Any, *, use_expected_amount: bool = False
    ) -> dict[str, Any]:
        """Build a purchase item dict from a non-installment Expense.

        When use_expected_amount=True (fixed recurring expenses), uses expected_monthly_amount
        for amount and None for date. Otherwise uses total_amount and expense_date.
        """
        cat_id, cat_name, cat_color, _sub_id, _sub_name = (
            FinancialDashboardService._resolve_category_fields(exp.category)
        )
        if use_expected_amount:
            amount = exp.expected_monthly_amount
            expense_date = None
        else:
            amount = exp.total_amount
            expense_date = exp.expense_date.isoformat() if exp.expense_date else None
        return {
            "description": exp.description,
            "amount": amount,
            "total_amount": None,
            "total_installments": None,
            "person_name": exp.person.name if exp.person else None,
            "card_name": exp.credit_card.nickname if exp.credit_card else None,
            "category_id": cat_id,
            "category_name": cat_name,
            "category_color": cat_color,
            "date": expense_date,
            "expense_type": exp.expense_type,
        }

    @staticmethod
    def _aggregate_purchases_by_category(
        items: list[dict[str, Any]], grand_total: Decimal
    ) -> list[dict[str, Any]]:
        """Aggregate purchase items by category and compute percentages."""
        category_map: dict[int | None, dict[str, Any]] = {}

        for item in items:
            key = item["category_id"]
            if key not in category_map:
                category_map[key] = {
                    "category_id": item["category_id"],
                    "category_name": item["category_name"],
                    "color": item["category_color"] or "#6B7280",
                    "total": Decimal("0.00"),
                    "count": 0,
                }
            category_map[key]["total"] += item["amount"]
            category_map[key]["count"] += 1

        result = []
        for entry in sorted(category_map.values(), key=lambda x: x["total"], reverse=True):
            percentage = (
                float(entry["total"] / grand_total * 100) if grand_total > Decimal("0.00") else 0.0
            )
            result.append(
                {
                    "category_id": entry["category_id"],
                    "category_name": entry["category_name"] or "Sem Categoria",
                    "color": entry["color"],
                    "total": entry["total"],
                    "percentage": round(percentage, 2),
                    "count": entry["count"],
                }
            )

        return result

    @staticmethod
    def _build_fixed_expense_categories_detail(
        month_start: date,
    ) -> dict[str, dict[str, Any]]:
        """Categorize fixed expenses + orphan one-time expenses — with enriched items."""
        next_month = month_start.replace(day=28) + timedelta(days=4)
        next_month = next_month.replace(day=1)

        fixed_expenses = (
            Expense.objects.filter(
                expense_type=ExpenseType.FIXED_EXPENSE,
                is_recurring=True,
                is_offset=False,
                person__isnull=True,
            )
            .exclude(end_date__lt=month_start)
            .select_related("category", "category__parent")
        )

        orphan_one_time = Expense.objects.filter(
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            is_offset=False,
            person__isnull=True,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).select_related("category", "category__parent")

        internet: list[dict[str, Any]] = []
        internet_total = Decimal("0.00")
        celular: list[dict[str, Any]] = []
        celular_total = Decimal("0.00")
        sitio: list[dict[str, Any]] = []
        sitio_total = Decimal("0.00")
        outros: list[dict[str, Any]] = []
        outros_total = Decimal("0.00")

        def _make_detail_item(exp: Expense, amount: Decimal) -> dict[str, Any]:
            cat_id, cat_name, cat_color, sub_id, sub_name = (
                FinancialDashboardService._resolve_category_fields(exp.category)
            )
            return {
                "expense_id": exp.id,
                "installment_id": None,
                "description": exp.description,
                "installment_number": None,
                "total_installments": None,
                "category_id": cat_id,
                "category_name": cat_name,
                "category_color": cat_color,
                "subcategory_id": sub_id,
                "subcategory_name": sub_name,
                "notes": exp.notes,
                "amount": amount,
                "due_date": None,
            }

        for exp in fixed_expenses:
            amount = exp.expected_monthly_amount or exp.total_amount
            item = _make_detail_item(exp, amount)
            desc_lower = exp.description.lower()

            if "internet" in desc_lower:
                internet.append(item)
                internet_total += amount
            elif "claro" in desc_lower:
                celular.append(item)
                celular_total += amount
            elif "sítio" in desc_lower or "sitio" in desc_lower or "ração" in desc_lower:
                sitio.append(item)
                sitio_total += amount
            else:
                outros.append(item)
                outros_total += amount

        for exp in orphan_one_time:
            amount = exp.total_amount
            item = _make_detail_item(exp, amount)
            outros.append(item)
            outros_total += amount

        return {
            "internet": {"total": internet_total, "details": internet},
            "celular": {"total": celular_total, "details": celular},
            "sitio": {"total": sitio_total, "details": sitio},
            "outros_fixed": {"total": outros_total, "details": outros},
        }
