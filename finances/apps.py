import importlib
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FinancesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "finances"

    def ready(self) -> None:
        """Import signal handlers when the app is ready.

        A failure here means cache invalidation is silently broken app-wide (every finance
        write would leave stale finance-* caches with no error surfaced) — this must fail
        loud at startup, not be swallowed into a log line.
        """
        importlib.import_module(".signals", package="finances")
        logger.info("Finances app signals registered successfully")
