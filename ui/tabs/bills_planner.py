from typing import Any, List, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.database import SessionLocal
from core.models import Bill
from core.state import global_state


class BillsPlannerTab(QWidget):
    """A QWidget tab for planning and managing recurring bills and lifestyle expenses.

    This tab allows users to add, view, edit, and delete bill entries,
    categorizing them as fixed obligations or weekly lifestyle expenses.
    It interacts with the application's database for data persistence.
    """

    def __init__(self) -> None:
        """Initializes the BillsPlannerTab.

        Sets up the user interface, loads existing bill data into two separate
        tables (fixed and lifestyle), and connects to the global state's
        data update signal to refresh the UI.
        """
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.setup_ui()
        self.load_data()

        global_state.data_updated.connect(self.load_data)

    def setup_ui(self) -> None:
        """Sets up the user interface components for the Bills Planner tab.

        This includes input fields for bill details (type, category, description,
        amount, currency, frequency), buttons for adding and deleting bills,
        and two table views to display fixed monthly bills and weekly lifestyle
        expenses separately.
        """
        # Top Form
        form_layout = QHBoxLayout()

        self.obligation_type_input = QComboBox()
        self.obligation_type_input.addItems(["Fixed Obligation", "Weekly Lifestyle"])

        self.cat_input = QComboBox()
        self.cat_input.addItems(["Housing", "Utilities", "Food", "Internet", "Subscriptions", "Misc"])
        self.cat_input.setEditable(True)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description")

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Amount")

        self.curr_input = QComboBox()
        self.curr_input.addItems(["PHP", "USD", "GBP"])
        self.curr_input.setEditable(True)

        self.freq_input = QComboBox()
        self.freq_input.addItems(["monthly", "weekly", "annual"])

        add_btn = QPushButton("Add Obligation")
        add_btn.clicked.connect(self.add_bill)

        form_layout.addWidget(self.obligation_type_input)
        form_layout.addWidget(self.cat_input)
        form_layout.addWidget(self.desc_input)
        form_layout.addWidget(self.amount_input)
        form_layout.addWidget(self.curr_input)
        form_layout.addWidget(self.freq_input)
        form_layout.addWidget(add_btn)

        self.layout.addLayout(form_layout)

        # Fixed Monthly Bills Table
        self.layout.addWidget(QLabel("Fixed Monthly Bills"))
        self.fixed_model = QStandardItemModel(0, 5)
        self.fixed_model.setHorizontalHeaderLabels(["ID", "Category", "Description", "Gross Amount", "Freq"])
        self.fixed_table = QTableView()
        self.fixed_table.setModel(self.fixed_model)
        self.fixed_table.setColumnHidden(0, True)
        self.fixed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fixed_table.setEditTriggers(QTableView.DoubleClicked)
        self.fixed_model.itemChanged.connect(lambda item: self.handle_item_changed(item, is_fixed=True))
        self.layout.addWidget(self.fixed_table)
        self.delete_fixed_btn = QPushButton("Delete Selected Fixed Bill")
        self.delete_fixed_btn.clicked.connect(lambda: self.delete_item(is_fixed=True))
        self.layout.addWidget(self.delete_fixed_btn)

        # Weekly Lifestyle Table
        self.layout.addWidget(QLabel("Weekly Lifestyle"))
        self.lifestyle_model = QStandardItemModel(0, 5)
        self.lifestyle_model.setHorizontalHeaderLabels(["ID", "Category", "Description", "Gross Amount", "Freq"])
        self.lifestyle_table = QTableView()
        self.lifestyle_table.setModel(self.lifestyle_model)
        self.lifestyle_table.setColumnHidden(0, True)
        self.lifestyle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lifestyle_table.setEditTriggers(QTableView.DoubleClicked)
        self.lifestyle_model.itemChanged.connect(lambda item: self.handle_item_changed(item, is_fixed=False))
        self.layout.addWidget(self.lifestyle_table)
        self.delete_weekly_btn = QPushButton("Delete Selected Lifestyle Item")
        self.delete_weekly_btn.clicked.connect(lambda: self.delete_item(is_fixed=False))
        self.layout.addWidget(self.delete_weekly_btn)

    def load_data(self) -> None:
        """Loads bill data from the database and populates the table views.

        Clears existing data in both fixed and lifestyle bill tables, then
        queries the database for all bill entries. Each bill is then added
        to the appropriate table based on its `is_fixed` status.
        """
        self.fixed_model.removeRows(0, self.fixed_model.rowCount())
        self.lifestyle_model.removeRows(0, self.lifestyle_model.rowCount())

        with SessionLocal() as db:
            bills: List[Bill] = db.query(Bill).all()
            for bill in bills:
                model = self.fixed_model if bill.is_fixed else self.lifestyle_model
                self.add_bill_to_model(model, bill)

    def add_bill_to_model(self, model: QStandardItemModel, bill: Bill) -> None:
        """Adds a single bill entry to the specified QStandardItemModel.

        Args:
            model: The QStandardItemModel (either fixed_model or lifestyle_model)
                to which the bill data will be added.
            bill: The Bill object containing the data to be displayed.
        """
        row = [
            QStandardItem(str(bill.id)),
            QStandardItem(bill.category),
            QStandardItem(bill.description or ""),
            QStandardItem(f"{bill.amount:.2f} {bill.currency}"),
            QStandardItem(bill.frequency.capitalize()),
        ]
        model.appendRow(row)

    @Slot(QStandardItem)
    def handle_item_changed(self, item: QStandardItem, is_fixed: bool) -> None:
        """Handles changes made directly in the table view and updates the database.

        This slot is triggered when an item in either the fixed or lifestyle
        bill table is edited. It retrieves the updated value and the corresponding
        bill ID, then updates the relevant field in the database. Includes
        input validation for the amount field.

        Args:
            item: The QStandardItem that was changed.
            is_fixed: A boolean indicating whether the change occurred in the
                fixed bills table (True) or lifestyle bills table (False).
        """
        model = self.fixed_model if is_fixed else self.lifestyle_model

        # Get the ID from the first column
        bill_id: int = int(model.item(item.row(), 0).text())

        with SessionLocal() as session:
            bill: Optional[Bill] = session.query(Bill).get(bill_id)
            if not bill:
                return

            # Map column to attribute
            column: int = item.column()
            new_value: str = item.text()

            if column == 1:  # Category
                bill.category = new_value
            elif column == 2:  # Description
                bill.description = new_value
            elif column == 3:  # Gross Amount
                try:
                    amount_str, currency = new_value.split()
                    bill.amount = float(amount_str)
                    bill.currency = currency
                except ValueError:
                    QMessageBox.warning(self, "Input Error", "Invalid amount format. Please use 'AMOUNT CURRENCY' (e.g., '123.45 USD').")
                    self.load_data()  # Revert change on error
                    return
            elif column == 4:  # Freq
                bill.frequency = new_value.lower()

            session.commit()
            global_state.data_updated.emit()

    def add_bill(self) -> None:
        """Adds a new bill entry to the database based on form input.

        Validates the amount input, then creates a new Bill object with data
        from the form fields. The new bill is added to the database, and the
        UI is updated.
        """
        try:
            amount: float = float(self.amount_input.text())
        except ValueError:
            QMessageBox.warning(self, "Syntax Error", "Amount must be a valid number.")
            return

        with SessionLocal() as db:
            new_bill = Bill(
                category=self.cat_input.currentText(),
                description=self.desc_input.text(),
                amount=amount,
                currency=self.curr_input.currentText(),
                frequency=self.freq_input.currentText(),
                is_fixed=(self.obligation_type_input.currentText() == "Fixed Obligation"),
                spent_this_month=0.0,
            )
            db.add(new_bill)
            db.commit()

        self.amount_input.clear()
        self.desc_input.clear()

        global_state.data_updated.emit()

    def delete_item(self, is_fixed: bool) -> None:
        """Deletes the selected bill entry from the database.

        Prompts the user for confirmation before deleting. If confirmed, the
        corresponding bill record is removed from the database, and the UI is
        updated.

        Args:
            is_fixed: A boolean indicating whether the bill to be deleted is
                from the fixed bills table (True) or lifestyle bills table (False).
        """
        table = self.fixed_table if is_fixed else self.lifestyle_table
        model = self.fixed_model if is_fixed else self.lifestyle_model

        selected_indexes = table.selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "No Selection", "Please select an item to delete.")
            return

        # Get the ID from the first column of the selected row
        row: int = selected_indexes[0].row()
        bill_id: int = int(model.item(row, 0).text())

        reply = QMessageBox.question(
            self,
            "Delete Confirmation",
            f"Are you sure you want to delete bill ID {bill_id}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            with SessionLocal() as session:
                bill: Optional[Bill] = session.query(Bill).get(bill_id)
                if bill:
                    session.delete(bill)
                    session.commit()
                    global_state.data_updated.emit()
                    self.load_data()
