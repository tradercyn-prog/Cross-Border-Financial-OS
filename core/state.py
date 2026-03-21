from typing import Any, Dict

from PySide6.QtCore import QObject, Signal

from core.database import SessionLocal
from core.models import Settings


class StateManager(QObject):
    """Central Nervous System for the Cross-Border Financial OS.

    This class manages the application's global state, including currency settings
    and various metrics. It inherits from QObject to enable signal-slot communication
    for UI updates when data changes in the database.
    """

    data_updated = Signal()

    def __init__(self) -> None:
        """Initializes the StateManager.

        Sets up default base and local currencies, initializes an empty dictionary
        for metrics, and defines a mapping for currency symbols.
        """
        super().__init__()
        self.base_currency: str = "USD"
        self.local_currency: str = "PHP"
        self.metrics: Dict[str, Any] = {}
        self.currency_symbols: Dict[str, str] = {
            "USD": "$",
            "PHP": "₱",
            "JPY": "¥",
            "EUR": "€",
            "GBP": "£",
            "AUD": "A$",
            "CAD": "C$",
            "SGD": "S$",
            "THB": "฿",
            "NZD": "NZ$",
            "KRW": "₩",
            "VND": "₫",
        }

    def get_metric(self, key: str, default: Any = None) -> Any:
        """Retrieves a metric from the state manager.

        Args:
            key: The string key of the metric to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The value of the metric associated with the key, or the default value
            if the key does not exist.
        """
        return self.metrics.get(key, default)

    def set_metric(self, key: str, value: Any) -> None:
        """Sets a metric in the state manager.

        Args:
            key: The string key of the metric to set.
            value: The value to assign to the metric.
        """
        self.metrics[key] = value

    def load_settings(self) -> None:
        """Loads application settings from the database.

        Retrieves the base and local currency settings from the 'settings' table.
        If no settings are found, default settings are created and saved to the database.
        The loaded settings update the `base_currency` and `local_currency` attributes
        of the StateManager instance.
        """
        db = SessionLocal()
        settings = db.query(Settings).first()
        if not settings:
            settings = Settings()
            db.add(settings)
            db.commit()
        self.base_currency = settings.base_currency
        self.local_currency = settings.local_currency
        db.close()


# Instantiate a single global instance
global_state = StateManager()
