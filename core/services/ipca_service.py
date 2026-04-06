"""IPCA index service for rent adjustment calculations.

Fetches IPCA monthly index values from the IBGE SIDRA API (table 1737,
variable 2266) and calculates adjustment factors between two months.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from core.models import IPCAIndex

logger = logging.getLogger(__name__)

_SIDRA_BASE_URL = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/{period}/d/v2266%2013"
_REQUEST_TIMEOUT = 15


class IPCAService:
    """Service for fetching and calculating IPCA-based rent adjustments."""

    @staticmethod
    def fetch_latest() -> IPCAIndex | None:
        """Fetch missing IPCA indices from IBGE SIDRA API.

        Checks the latest index in the database and fetches any newer months.
        Returns the most recent index after fetching.
        """
        latest = IPCAIndex.objects.order_by("-reference_month").first()

        if latest:
            start = latest.reference_month + relativedelta(months=1)
            period = f"{start.strftime('%Y%m')}-{timezone.now().date().strftime('%Y%m')}"
        else:
            # First run: fetch last 24 months
            start = timezone.now().date() - relativedelta(months=24)
            period = f"{start.strftime('%Y%m')}-{timezone.now().date().strftime('%Y%m')}"

        url = _SIDRA_BASE_URL.format(period=period)
        logger.info("Fetching IPCA indices from SIDRA: %s", period)

        try:
            response = requests.get(url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            logger.warning("Failed to fetch IPCA data from IBGE SIDRA API")
            return IPCAIndex.objects.order_by("-reference_month").first()

        data = response.json()
        if not isinstance(data, list) or len(data) <= 1:
            logger.info("No new IPCA data available")
            return IPCAIndex.objects.order_by("-reference_month").first()

        created_count = 0
        for row in data[1:]:  # Skip header row
            period_code = row.get("D3C", "")
            value_str = row.get("V", "")

            if not period_code or not value_str or value_str in ("...", "-"):
                continue

            try:
                year = int(period_code[:4])
                month = int(period_code[4:6])
                ref_month = date(year, month, 1)
                value = Decimal(value_str)
            except (ValueError, InvalidOperation):
                logger.warning("Invalid IPCA data: period=%s value=%s", period_code, value_str)
                continue

            _, created = IPCAIndex.objects.update_or_create(
                reference_month=ref_month,
                defaults={"value": value},
            )
            if created:
                created_count += 1

        if created_count > 0:
            logger.info("Saved %d new IPCA index records", created_count)

        return IPCAIndex.objects.order_by("-reference_month").first()

    @staticmethod
    def get_adjustment_factor(start_month: date, end_month: date) -> Decimal | None:
        """Calculate the IPCA adjustment factor between two months.

        Uses the index of the month BEFORE the start (as per IBGE methodology)
        and the index of the end month.

        Returns:
            Factor as Decimal (e.g., 1.0517 for 5.17%), or None if indices unavailable.
        """
        # IBGE methodology: use index of month before start
        index_start_month = start_month - relativedelta(months=1)
        index_start_month = index_start_month.replace(day=1)
        end_month = end_month.replace(day=1)

        try:
            start_index = IPCAIndex.objects.get(reference_month=index_start_month)
            end_index = IPCAIndex.objects.get(reference_month=end_month)
        except IPCAIndex.DoesNotExist:
            return None

        if start_index.value == 0:
            return None

        return end_index.value / start_index.value

    @staticmethod
    def get_adjustment_percentage(start_month: date, end_month: date) -> Decimal | None:
        """Calculate the IPCA adjustment percentage between two months.

        Returns:
            Percentage as Decimal (e.g., 5.17 for 5.17%), or None if indices unavailable.
        """
        factor = IPCAService.get_adjustment_factor(start_month, end_month)
        if factor is None:
            return None
        return ((factor - Decimal(1)) * Decimal(100)).quantize(Decimal("0.01"))

    @staticmethod
    def get_latest_available_month() -> date | None:
        """Return the most recent month available in the database."""
        latest = IPCAIndex.objects.order_by("-reference_month").first()
        return latest.reference_month if latest else None
