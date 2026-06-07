import importlib
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FinancesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "finances"

    def ready(self) -> None:
        """Import signal handlers when the app is ready."""
        try:
            importlib.import_module(".signals", package="finances")
            logger.info("Finances app signals registered successfully")
        except Exception:
            logger.exception("Error registering finances signals")
