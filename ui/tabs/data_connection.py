import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.database import SessionLocal
from core.models import Asset
from core.state import global_state
from integrations.csv_ingestion import SchwabParser
from integrations.exchange_rates import exchange_rate_provider


class DataConnectionTab(QWidget):
    """UI Tab for managing data connections, including CSV import and live FX rates.

    This tab provides functionalities for users to import brokerage asset data
    from Schwab CSV files, preview the parsed data, and commit it to the
    application's database. It also allows fetching and displaying live
    exchange rates.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initializes the DataConnectionTab.

        Args:
            parent: The parent QWidget for this tab.
        """
        super().__init__(parent)
        self.setWindowTitle("Data Connections")
        self.parser = SchwabParser()
        self.parsed_data: List[Dict[str, Any]] = []

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Schwab CSV Ingestion ---
        self.schwab_label = QLabel("Import Brokerage Holdings from Schwab CSV")
        self.schwab_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.select_csv_button = QPushButton("Select Schwab CSV")
        self.select_csv_button.clicked.connect(self.open_csv_dialog)

        self.preview_table = QTableView()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_model = QStandardItemModel(self)
        self.preview_table.setModel(self.preview_model)

        self.confirm_button = QPushButton("Confirm & Overwrite Brokerage Assets")
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.confirm_and_overwrite)

        self.layout.addWidget(self.schwab_label)
        self.layout.addWidget(self.select_csv_button)
        self.layout.addWidget(self.preview_table)
        self.layout.addWidget(self.confirm_button)

        # --- FX Rate Section ---
        self.fx_rate_label = QLabel("Live FX Rate (USD to PHP): Not fetched yet")
        self.fetch_fx_button = QPushButton("Fetch Live FX Rate")
        self.fetch_fx_button.clicked.connect(self.fetch_live_fx_rate)

        self.layout.addSpacing(20)
        self.layout.addWidget(self.fx_rate_label)
        self.layout.addWidget(self.fetch_fx_button)

    def open_csv_dialog(self) -> None:
        """Opens a file dialog to select a Schwab CSV file.

        Upon selection, the file is parsed using `SchwabParser`. If parsing
        is successful and data is found, the preview table is populated, and
        the confirm button is enabled. Error messages are displayed for
        parsing failures or empty files.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Schwab CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.parsed_data = self.parser.parse(file_path)
                if self.parsed_data:
                    self.populate_preview_table()
                    self.confirm_button.setEnabled(True)
                else:
                    QMessageBox.warning(self, "Parsing Error", "Could not find any valid asset data in the selected CSV.")
                    self.clear_preview()
            except Exception as e:
                logging.error(f"An error occurred while reading the file: {e}", exc_info=True)
                QMessageBox.critical(self, "File Error", f"An error occurred while reading the file: {e}")
                self.clear_preview()

    def populate_preview_table(self) -> None:
        """Fills the QTableView with data parsed from the CSV.

        The preview table displays the asset name, balance, and currency of
        the assets extracted from the CSV file. All items in the preview
        table are set to be non-editable.
        """
        self.preview_model.clear()
        self.preview_model.setHorizontalHeaderLabels(["Asset", "Balance", "Currency"])
        for item in self.parsed_data:
            row = [
                QStandardItem(str(item.get("asset_name", "N/A"))),
                QStandardItem(f"{item.get('balance', 0.0):,.2f}"),
                QStandardItem(str(item.get("currency", "USD"))),
            ]
            for col in row:
                col.setEditable(False)
            self.preview_model.appendRow(row)

    def clear_preview(self) -> None:
        """Clears the preview table and disables the confirm button.

        Resets the UI elements related to CSV import, effectively clearing
        any previously loaded data and preventing accidental commits.
        """
        self.preview_model.clear()
        self.parsed_data = []
        self.confirm_button.setEnabled(False)

    def confirm_and_overwrite(self) -> None:
        """Commits the parsed Schwab CSV data to the database.

        This function performs a "scorched earth" replacement of brokerage assets.
        It first deletes all existing assets marked as 'Brokerage' and then
        inserts the new records from the parsed CSV file. After successful
        commit, it notifies the application of data changes and clears the UI.
        """
        if not self.parsed_data:
            logging.warning("Attempted to commit brokerage assets, but no parsed data was found.")
            return

        try:
            with SessionLocal() as session:
                # 1. SCORCHED EARTH: Wipe existing brokerage accounts
                deleted_count: int = session.query(Asset).filter(Asset.asset_type == "Brokerage").delete()
                logging.info(f"Wiped {deleted_count} old brokerage assets from DB.")

                # 2. Insert the fresh CSV data
                for item in self.parsed_data:
                    new_asset = Asset(
                        asset_type=item["asset_type"],
                        asset_name=item["asset_name"],
                        is_liquid=item["is_liquid"],
                        balance=item["balance"],
                        currency=item["currency"],
                        value_local=0.0,  # Set default, will be updated by a separate process
                    )
                    session.add(new_asset)

                session.commit()
                logging.info(f"Successfully committed {len(self.parsed_data)} new Schwab assets.")

            # 3. Notify the rest of the application that the data has changed
            global_state.data_updated.emit()

            # 4. Clean up the UI
            self.clear_preview()
            QMessageBox.information(self, "Success", f"Successfully overwrote and imported {len(self.parsed_data)} brokerage assets.")

        except Exception as e:
            logging.error(f"Failed to commit assets to database: {e}", exc_info=True)
            QMessageBox.critical(self, "Database Error", f"An error occurred while writing to the database: {e}")

    def fetch_live_fx_rate(self) -> None:
        """Fetches the live exchange rate and updates the UI.

        This method disables the fetch button during the API call, then
        retrieves the USD to PHP exchange rate using the `exchange_rate_provider`.
        The UI is updated with the fetched rate, or an error message if the
        fetch fails. The button is re-enabled after the operation.
        """
        self.fetch_fx_button.setEnabled(False)
        self.fetch_fx_button.setText("Fetching...")

        rate: Optional[float] = exchange_rate_provider.get_live_rate("USD", "PHP")

        self.fetch_fx_button.setEnabled(True)
        self.fetch_fx_button.setText("Fetch Live FX Rate")

        if rate is not None:
            self.fx_rate_label.setText(f"Live FX Rate (USD to PHP): {rate:.4f}")
            logging.info(f"Successfully updated FX rate in UI: {rate}")
        else:
            self.fx_rate_label.setText("Live FX Rate (USD to PHP): Failed to fetch")
            QMessageBox.warning(
                self,
                "Error",
                "Could not fetch the live exchange rate. "
                "Please check the logs and ensure your Wise API token is set up correctly.",
            )
