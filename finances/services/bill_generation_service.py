"""Recurring bill generation for the condominium (Phase 2, Session 37).

Generates the month's recurring Bills from active BillingAccounts (idempotent,
race-safe) plus the "paid up to X" seed line so unfilled bills surface as overdue.

Extension points (not this phase): Session 41 extends ensure_month_bills with
Installment lines from non-embedded plans; Session 44 with payroll. Embedded
installments become a line on the recurring account's Bill, never their own Bill.
"""

import logging
from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from core.services.rent_schedule_service import RentScheduleService
from finances.models import (
    Bill,
    BillBehavior,
    BillingAccount,
    BillingAccountState,
    BillLifecycleState,
    BillLineItem,
    BillSkip,
)

logger = logging.getLogger(__name__)


class BillGenerationService:
    """Stateless recurring-bill generation."""

    @staticmethod
    def _due_date_for(account: BillingAccount, year: int, month: int) -> date:
        """Pure date generator: account.default_due_day clamped to the month (31 -> 28/29/30)."""
        return date(
            year, month, RentScheduleService.clamp_due_day(account.default_due_day, year, month)
        )

    @staticmethod
    def _is_account_eligible(account: BillingAccount, month_start: date) -> bool:
        """Active, within tracking_start_month..end_date, and not skipped for the month."""
        if account.lifecycle_state != BillingAccountState.ACTIVE:
            return False
        if account.tracking_start_month is not None and account.tracking_start_month > month_start:
            return False
        if account.end_date is not None and account.end_date < month_start:
            return False
        return not BillSkip.objects.filter(
            billing_account=account, reference_month=month_start
        ).exists()

    @staticmethod
    def ensure_month_bills(year: int, month: int, user: User | None = None) -> list[Bill]:
        """Ensure one recurring Bill per eligible BillingAccount for (year, month).

        Idempotent and race-safe (get_or_create on the partial unique
        (billing_account, competence_month) + IntegrityError tolerance). Only recurring
        accounts — installments/payroll/embedded plans are skipped (their models arrive
        in Phase 3/4). Returns the ensured bills (created + already existing).
        """
        month_start = date(year, month, 1)
        bills: list[Bill] = []
        for account in BillingAccount.objects.filter(lifecycle_state=BillingAccountState.ACTIVE):
            if not BillGenerationService._is_account_eligible(account, month_start):
                continue
            bills.append(BillGenerationService._ensure_account_bill(account, year, month, user))
        return bills

    @staticmethod
    def _ensure_account_bill(
        account: BillingAccount, year: int, month: int, user: User | None
    ) -> Bill:
        month_start = date(year, month, 1)
        defaults = {
            "condominium": account.condominium,
            "building": account.building,
            "category": account.category,
            "behavior": BillBehavior.RECURRING,
            "lifecycle_state": BillLifecycleState.ACTIVE,
            "due_date": BillGenerationService._due_date_for(account, year, month),
            "description": account.name,
            "external_identifier": account.external_identifier,
            "created_by": user,
            "updated_by": user,
        }
        with transaction.atomic():
            try:
                bill, created = Bill.all_objects.get_or_create(
                    billing_account=account,
                    competence_month=month_start,
                    is_deleted=False,
                    defaults=defaults,
                )
            except IntegrityError:
                # Lost the race on the partial unique — re-fetch the active bill.
                bill = Bill.objects.get(billing_account=account, competence_month=month_start)
                created = False
            # Seed only a freshly created bill (idempotent re-runs add no duplicate lines).
            if created and account.expected_amount > 0:
                BillLineItem.objects.create(
                    bill=bill,
                    description=account.name,
                    amount=account.expected_amount,
                    is_offset=False,
                    category=account.category,
                    created_by=user,
                    updated_by=user,
                )
        return bill
