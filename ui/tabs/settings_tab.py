from typing import List, Optional

from PySide6.QtWidgets import QComboBox, QFormLayout, QPushButton, QVBoxLayout, QWidget

from core.database import SessionLocal
from core.models import Settings
from core.state import global_state


class SettingsTab(QWidget):
    """A QWidget tab for managing application settings, specifically currency preferences.

    This tab allows users to select their base and local currencies, which are
    then saved to the database and updated in the global application state.
    Changes to these settings trigger a global data update to refresh dependent UI elements.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initializes the SettingsTab.

        Sets up the user interface with currency selection combo boxes and a
        save button. It also loads the initial currency settings from the
        global state.

        Args:
            parent: The parent QWidget for this tab.
        """
        super().__init__(parent)
        self.currencies: List[str] = ["USD", "PHP", "JPY", "EUR", "GBP", "THB", "AUD", "CAD", "NZD"]

        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.base_currency_combo = QComboBox()
        self.base_currency_combo.addItems(self.currencies)

        self.local_currency_combo = QComboBox()
        self.local_currency_combo.addItems(self.currencies)

        self.form_layout.addRow("Base Currency (Home):", self.base_currency_combo)
        self.form_layout.addRow("Local Currency (Current):", self.local_currency_combo)

        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.save_button)

        self.load_initial_settings()

    def load_initial_settings(self) -> None:
        """Loads the current base and local currency settings into the combo boxes.

        Retrieves the current currency settings from the global application state
        and sets the selected items in the respective QComboBox widgets.
        """
        self.base_currency_combo.setCurrentText(global_state.base_currency)
        self.local_currency_combo.setCurrentText(global_state.local_currency)

    def save_settings(self) -> None:
        """Saves the selected currency settings to the database and updates global state.

        Retrieves the selected base and local currencies from the UI, updates
        the `Settings` record in the database, and then propagates these changes
        to the `global_state` object. Finally, it emits a `data_updated` signal
        to notify other parts of the application about the change.
        """
        db = SessionLocal()
        try:
            settings: Settings = db.query(Settings).first()
            if not settings:
                settings = Settings()
                db.add(settings)

            settings.base_currency = self.base_currency_combo.currentText()
            settings.local_currency = self.local_currency_combo.currentText()

            db.commit()

            global_state.base_currency = settings.base_currency
            global_state.local_currency = settings.local_currency
            global_state.data_updated.emit()
        finally:
            db.close()
