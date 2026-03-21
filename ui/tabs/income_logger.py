import sys
from typing import List, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.database import SessionLocal
from core.models import Income
from core.state import global_state
from integrations.wise_api import WiseClient


class IncomeLoggerTab(QWidget):
    """A QWidget tab for logging and managing income entries.

    This tab provides a user interface to record income details such as date,
    source, category, amount, and currency. It integrates with the application's
    database for persistence and can convert amounts to a base currency using
    exchange rates from the Wise API.
    """

    def __init__(self) -> None:
        """Initializes the IncomeLoggerTab.

        Sets up the user interface elements, loads existing income data, and
        connects to the global state's data update signal to ensure the UI
        reflects the latest data.
        """
        super().__init__()
        self.init_ui()
        self.load_data()
        global_state.data_updated.connect(self.load_data)

    def init_ui(self) -> None:
        """Initializes the user interface components for the Income Logger tab.

        This includes form fields for income details (date, source, category,
        amount, currency), a button to log income, and a table view to display
        all recorded income entries.
        """
        main_layout = QVBoxLayout(self)

        # --- Entry Form ---
        form_layout = QFormLayout()
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.source_edit = QLineEdit()

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Active/Freelance", "Passive/Investments", "Gig", "Other"])
        self.category_combo.setEditable(True)

        self.amount_spinbox = QDoubleSpinBox()
        self.amount_spinbox.setMaximum(1000000.00)
        self.amount_spinbox.setDecimals(2)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "PHP", "GBP", "EUR"])
        self.currency_combo.setEditable(True)

        form_layout.addRow("Date:", self.date_edit)
        form_layout.addRow("Source:", self.source_edit)
        form_layout.addRow("Category:", self.category_combo)
        form_layout.addRow("Amount:", self.amount_spinbox)
        form_layout.addRow("Currency:", self.currency_combo)

        self.submit_button = QPushButton("Log Income")
        self.submit_button.clicked.connect(self.log_income)
        form_layout.addRow(self.submit_button)

        main_layout.addLayout(form_layout)

        # --- Data Table ---
        self.table_view = QTableView()
        self.model = QStandardItemModel()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)  # Make table read-only
        main_layout.addWidget(self.table_view)

    def load_data(self) -> None:
        """Loads income data from the database and populates the QTableView.

        Clears the existing table model and repopulates it with fresh data
        from the database, ordered by date in descending order. Displays
        income ID, date, source, category, raw amount, currency, and USD value.
        """
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["ID", "Date", "Source", "Category", "Raw Amount", "Currency", "USD Value"])

        db = SessionLocal()
        try:
            incomes: List[Income] = db.query(Income).order_by(Income.date.desc()).all()
            for income in incomes:
                row = [
                    QStandardItem(str(income.id)),
                    QStandardItem(income.date.strftime("%Y-%m-%d")),
                    QStandardItem(income.source),
                    QStandardItem(income.category),
                    QStandardItem(f"{income.input_amount:.2f}"),
                    QStandardItem(income.currency),
                    QStandardItem(f"{income.amount_local:.2f}"),
                ]
                self.model.appendRow(row)
        finally:
            db.close()

    def log_income(self) -> None:
        """Logs a new income entry to the database based on form input.

        Retrieves data from the form fields, converts the amount to USD if
        necessary using the Wise API, and then creates a new Income object.
        The new income is added to the database, and the UI is updated.
        Error messages are displayed if exchange rates cannot be retrieved.
        """
        db = SessionLocal()
        try:
            input_amount: float = self.amount_spinbox.value()
            currency: str = self.currency_combo.currentText()
            usd_value: float = input_amount

            if currency != "USD":
                wise_client = WiseClient()
                rate: Optional[float] = wise_client.get_exchange_rate(source=currency, target="USD")
                if rate:
                    usd_value = input_amount * rate
                else:
                    QMessageBox.warning(self, "Exchange Rate Error", f"Could not retrieve exchange rate for {currency}. Income not logged.")
                    return

            new_income = Income(
                date=self.date_edit.date().toPython(),
                source=self.source_edit.text(),
                category=self.category_combo.currentText(),
                input_amount=input_amount,
                currency=currency,
                amount_local=usd_value,
            )
            db.add(new_income)
            db.commit()
            global_state.data_updated.emit()
        finally:
            db.close()

        # Clear form and reload data
        self.source_edit.clear()
        self.date_edit.setDate(QDate.currentDate())
        self.category_combo.setCurrentIndex(0)
        self.amount_spinbox.setValue(0.0)
        self.currency_combo.setCurrentIndex(0)
