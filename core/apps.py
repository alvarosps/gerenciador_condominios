import importlib
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        """
        Import signal handlers when the app is ready.

        Phase 4: Connect cache invalidation signals.
        """
        try:
            importlib.import_module(".signals", package="core")
            logger.info("Core app signals registered successfully")
        except Exception:
            logger.exception("Error registering core signals")
