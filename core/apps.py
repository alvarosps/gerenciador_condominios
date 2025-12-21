import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """
        Import signal handlers when the app is ready.

        Phase 4: Connect cache invalidation signals.
        """
        try:
            # Import signals to register them
            from . import signals

            logger.info("Core app signals registered successfully")
        except Exception as e:
            logger.error(f"Error registering core signals: {e}")
