
import sys

from app.config import settings
from app.core.logging import setup_logging


def main():
    """Initialize and run the Vyapaari+ application."""
    setup_logging()
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    try:
        # Register database models before initializing the schema.
        import app.modules.auth.models
        import app.modules.billing.models
        import app.modules.business.models
        import app.modules.customers.models
        import app.modules.employees.models
        import app.modules.finance.models
        import app.modules.inventory.models
        import app.modules.products.models
        import app.modules.purchasing.grn_models
        import app.modules.purchasing.models
        import app.modules.reports.models
        import app.modules.suppliers.models
        from app.db.session import init_db

        init_db()
        logger.info("Database schema initialized successfully.")

    except ImportError as exc:
        logger.warning(
            "Application dependency or model import missing: %s",
            exc,
        )
    except Exception:
        logger.exception("Database initialization failed.")
        raise

    try:
        from PySide6.QtWidgets import QApplication

        from app.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName(settings.app_name)

        window = MainWindow()
        window.show()

        return app.exec()

    except ImportError:
        logger.info(
            "PySide6 not present or running in headless mode. "
            "Headless BOS service ready."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
