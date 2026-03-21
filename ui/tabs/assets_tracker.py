import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtSql import QSqlDatabase, QSqlTableModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
from core.models import Asset
from core.state import global_state
from integrations.exchange_rates import exchange_rate_provider


class AssetsTrackerTab(QWidget):
    """A QWidget tab for tracking and managing user assets.

    This tab provides a user interface for adding, updating, deleting, and
    viewing financial assets. It integrates with the application's database
    for persistence and with the Wise API for live balance synchronization.
    """

    def __init__(self) -> None:
        """Initializes the AssetsTrackerTab.

        Sets up the user interface elements, loads existing asset data, and
        connects to the global state's data update signal to ensure the UI
        reflects the latest data.
        """
        super().__init__()
        self.setup_ui()
        self.load_data()

        # Listen for global data changes and redraw the table
        global_state.data_updated.connect(self.load_data)

    def setup_ui(self) -> None:
        """Sets up the user interface components for the Assets Tracker tab.

        This includes form fields for asset details (type, name, liquidity,
        balance, currency, external ID), buttons for actions (add/update, delete,
        sync), and a table view to display the assets.
        """
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        # --- Form Fields ---
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(["Bank Account", "E-Wallet (PayPal/Cold Wallet/GCash)", "Brokerage", "Cash", "Other"])

        self.asset_name_input = QLineEdit()
        self.asset_name_input.setPlaceholderText("e.g., 'Wise USD', 'Schwab', 'GCash'")

        self.is_liquid_combo = QComboBox()
        self.is_liquid_combo.addItems(["Yes", "No"])

        self.balance_spinbox = QDoubleSpinBox()
        self.balance_spinbox.setMaximum(10000000.00)
        self.balance_spinbox.setDecimals(2)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "PHP", "BTC", "Other"])
        self.currency_combo.setEditable(True)

        self.external_id_input = QLineEdit()
        self.external_id_input.setPlaceholderText("e.g., 12345678 (Wise Balance ID)")

        self.submit_button = QPushButton("Add/Update Asset")
        self.submit_button.clicked.connect(self.log_asset)

        # --- Add widgets to form layout ---
        self.form_layout.addRow("Asset Type:", self.asset_type_combo)
        self.form_layout.addRow("Asset Name:", self.asset_name_input)
        self.form_layout.addRow("Is Liquid?:", self.is_liquid_combo)
        self.form_layout.addRow("Balance:", self.balance_spinbox)
        self.form_layout.addRow("Currency:", self.currency_combo)
        self.form_layout.addRow("External ID:", self.external_id_input)
        self.form_layout.addRow(self.submit_button)

        # --- Table View ---
        self.table_view = QTableView()
        self.model = QStandardItemModel()
        self.table_view.setModel(self.model)
        self.model.itemChanged.connect(self.handle_item_changed)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setEditTriggers(QTableView.DoubleClicked)  # Make table editable on double click

        # --- Add layouts to main layout ---
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.table_view)

        self.delete_button = QPushButton("Delete Selected Asset")
        self.delete_button.clicked.connect(self.delete_asset)
        self.main_layout.addWidget(self.delete_button)

        self.update_live_btn = QPushButton("Update Live Balances")
        self.update_live_btn.setEnabled(True)
        self.update_live_btn.clicked.connect(self.sync_wise_balances)
        self.main_layout.addWidget(self.update_live_btn)

    def delete_asset(self) -> None:
        """Deletes the selected asset from the database.

        Retrieves the ID of the asset selected in the table view and removes
        the corresponding record from the database. After deletion, it triggers
        a data update to refresh the UI.
        """
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return  # No item selected

        row = selected_indexes[0].row()
        asset_id = self.model.item(row, 0).text()

        with SessionLocal() as session:
            asset_to_delete = session.query(Asset).filter(Asset.id == int(asset_id)).first()
            if asset_to_delete:
                session.delete(asset_to_delete)
                session.commit()
                global_state.data_updated.emit()

        self.load_data()

    def log_asset(self) -> None:
        """Creates a new asset or updates an existing one in the database.

        Gathers data from the form fields, checks if an asset with the given
        name already exists. If so, it updates the existing asset; otherwise,
        a new asset record is created. The changes are committed to the database,
        and the UI is updated.
        """
        asset_name: str = self.asset_name_input.text()
        if not asset_name:
            QMessageBox.warning(self, "Input Error", "Asset Name cannot be empty.")
            return

        with SessionLocal() as session:
            existing_asset: Optional[Asset] = session.query(Asset).filter(Asset.asset_name == asset_name).first()

            if existing_asset:
                # Update existing asset
                existing_asset.asset_type = self.asset_type_combo.currentText()
                existing_asset.balance = self.balance_spinbox.value()
                existing_asset.is_liquid = self.is_liquid_combo.currentText() == "Yes"
                existing_asset.currency = self.currency_combo.currentText()
                existing_asset.external_id = self.external_id_input.text()
            else:
                # Create new asset
                new_asset = Asset(
                    asset_type=self.asset_type_combo.currentText(),
                    asset_name=asset_name,
                    is_liquid=self.is_liquid_combo.currentText() == "Yes",
                    balance=self.balance_spinbox.value(),
                    currency=self.currency_combo.currentText(),
                    external_id=self.external_id_input.text(),
                    value_local=0.0,  # Or calculate appropriately
                )
                session.add(new_asset)

            session.commit()
            global_state.data_updated.emit()

        self.clear_form()
        self.load_data()

    def load_data(self) -> None:
        """Queries the Asset table and populates the QTableView with current asset data.

        Clears the existing table model and repopulates it with fresh data
        from the database, including asset ID, type, name, liquidity status,
        balance, currency, and external ID.
        """
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["ID", "Type", "Name", "Liquid?", "Balance", "Currency", "External ID"])

        with SessionLocal() as session:
            assets: List[Asset] = session.query(Asset).all()
            for asset in assets:
                row = [
                    QStandardItem(str(asset.id)),
                    QStandardItem(asset.asset_type),
                    QStandardItem(asset.asset_name),
                    QStandardItem("Yes" if asset.is_liquid else "No"),
                    QStandardItem(f"{asset.balance:,.2f}"),
                    QStandardItem(asset.currency),
                    QStandardItem(asset.external_id if asset.external_id else ""),
                ]
                self.model.appendRow(row)

    def clear_form(self) -> None:
        """Clears all input fields in the asset entry form.

        Resets the combo boxes to their default selections and clears the
        text and spin box inputs, preparing the form for a new entry.
        """
        self.asset_type_combo.setCurrentIndex(0)
        self.asset_name_input.clear()
        self.is_liquid_combo.setCurrentIndex(0)
        self.balance_spinbox.setValue(0.00)
        self.currency_combo.setCurrentIndex(0)
        self.external_id_input.clear()

    def handle_item_changed(self, item: QStandardItem) -> None:
        """Saves changes made directly in the table view back to the database.

        This slot is connected to the `itemChanged` signal of the table model.
        It specifically handles updates to the 'External ID' column, updating
        the corresponding asset record in the database.

        Args:
            item: The QStandardItem that was changed in the table view.
        """
        column: int = item.column()
        if column == 6:  # 'External ID' column
            row: int = item.row()
            asset_id: str = self.model.item(row, 0).text()
            new_external_id: str = item.text()

            with SessionLocal() as session:
                asset_to_update: Optional[Asset] = session.query(Asset).filter(Asset.id == int(asset_id)).first()
                if asset_to_update:
                    asset_to_update.external_id = new_external_id
                    session.commit()
                    # No need to emit here, as it can cause a loop if the view is reloaded.
                    # The user can manually refresh if needed.

    def sync_wise_balances(self) -> None:
        """Fetches live balances from Wise and updates corresponding assets in the database.

        This method attempts to synchronize asset balances with live data from
        the Wise API. It matches Wise balances to local assets using their
        `external_id`. It also calculates the local value of updated assets
        using current exchange rates and provides UI feedback on the sync status.
        """
        try:
            balances: List[Dict[str, Any]] = exchange_rate_provider.wise_client.get_live_balances()
            if not balances:
                QMessageBox.warning(self, "API Error", "No balances returned from Wise. Check terminal for API errors.")
                return

            # Create lookup map with strict string stripping
            balance_map: Dict[str, Dict[str, Any]] = {str(b["id"]).strip(): b for b in balances}
            logging.info(f"API returned: {balance_map}")

            updated_count: int = 0
            debug_matches: List[str] = []

            with SessionLocal() as db:
                for asset in db.query(Asset).all():
                    # Strict string stripping for the SQLite ID
                    ext_id: str = str(asset.external_id).strip() if asset.external_id else ""

                    if ext_id and ext_id in balance_map:
                        balance_info: Dict[str, Any] = balance_map[ext_id]
                        # 1. Update the raw balance
                        asset.balance = float(balance_info["balance"])

                        # 2. Update the local PHP value for accurate Net Worth
                        if asset.currency != global_state.local_currency:
                            rate: Optional[float] = exchange_rate_provider.get_live_rate(asset.currency, global_state.local_currency)
                            asset.value_local = asset.balance * (rate if rate is not None else 56.0)
                        else:
                            asset.value_local = asset.balance

                        updated_count += 1
                        debug_matches.append(f"{asset.asset_name}: {asset.balance:,.2f} {asset.currency}")

                        # Remove the matched ID from the map
                        del balance_map[ext_id]

                db.commit()

            # Force the UI nervous system to redraw
            global_state.data_updated.emit()

            # Visual Feedback
            if updated_count > 0 and not balance_map:
                QMessageBox.information(self, "Sync Successful", f"Successfully synced {updated_count} accounts:\n\n" + "\n".join(debug_matches))
            elif updated_count > 0 and balance_map:
                leftover_details: List[str] = [f"- {b['currency']} ({b.get('profile_type', 'N/A')}): {b['id']}" for b in balance_map.values()]
                QMessageBox.warning(
                    self,
                    "Partial Sync",
                    f"Synced {updated_count} accounts, but some API balances had no matching database asset.\n\nUnmatched API Balances:\n" + "\n".join(leftover_details),
                )
            else:
                api_details: List[str] = [f"- {b['currency']} ({b.get('profile_type', 'N/A')}): {b['id']}" for b in balance_map.values()]
                QMessageBox.warning(
                    self,
                    "Mapping Failed",
                    f"Wise API returned balances, but NO database IDs matched.\n\nAPI Balances Found:\n" + "\n".join(api_details),
                )

        except Exception as e:
            logging.error(f"The sync function crashed: {e}", exc_info=True)
            QMessageBox.critical(self, "Fatal Crash", f"The sync function crashed:\n{str(e)}")
