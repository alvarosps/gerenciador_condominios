"""Combined monthly calendar for the condominium (Session 38, design §8).

Entries (rent) reuse RentScheduleService.get_month_schedule (DRY — collectibility and
clamping are not reimplemented); exits (bills) are grouped by the day of their due_date
within the month. Two sections per day; no money KPIs (balance/cash/reserve are Phase 4).
"hoje / mês atual" via the São Paulo timezone helper. The endpoint is uncached (design §11).
"""

from decimal import Decimal
from typing import Any

from core.services.rent_schedule_service import RentScheduleService
from finances.models import Bill
from finances.money import money_str
from finances.services.timezone import today_sp


def _bill_exit(bill: Bill) -> dict[str, Any]:
    return {
        "bill_id": bill.pk,
        "description": bill.description,
        "building_number": bill.building.street_number if bill.building else None,
        "category": bill.category.name if bill.category else None,
        "amount_total": money_str(getattr(bill, "amount_total", Decimal(0))),
        "amount_remaining": money_str(getattr(bill, "amount_remaining", Decimal(0))),
        "payment_status": str(getattr(bill, "payment_status", "open")),
        "due_date": bill.due_date.isoformat(),
        "is_overdue": bool(getattr(bill, "is_overdue", False)),
        "lifecycle_state": bill.lifecycle_state,
    }


class CondoCalendarService:
    """Stateless combined (rent + bills) monthly calendar."""

    @staticmethod
    def combined_month(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        today = today_sp()
        rent = RentScheduleService.get_month_schedule(year, month, building_id)

        bills = (
            Bill.objects.with_amounts(today)
            .filter(due_date__year=year, due_date__month=month)
            .select_related("building", "category")
        )
        if building_id is not None:
            bills = bills.filter(building_id=building_id)

        exits_by_day: dict[int, list[dict[str, Any]]] = {}
        for bill in bills:
            exits_by_day.setdefault(bill.due_date.day, []).append(_bill_exit(bill))

        days = [
            {
                "day": rent_day["day"],
                "date": rent_day["date"],
                "weekday": rent_day["weekday"],
                "rent_entries": rent_day["items"],
                "bill_exits": exits_by_day.get(rent_day["day"], []),
            }
            for rent_day in rent["days"]
        ]
        return {
            "year": year,
            "month": month,
            "today": today.isoformat(),
            "days": days,
        }
