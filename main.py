"""Main entry point for the Cross-Border Financial OS application.

This script initializes the database, loads application settings, and
starts the PySide6 graphical user interface.
"""

import sys

from PySide6.QtWidgets import QApplication

from core.database import init_db
from core.state import global_state
from ui.main_window import MainWindow


def main() -> None:
    """Initializes and runs the Cross-Border Financial OS application.

    This function performs the following steps:
    1. Initializes the SQLite database and creates necessary tables.
    2. Loads global application settings, such as currency preferences, from the database.
    3. Boots the PySide6 UI, creating and displaying the main application window.
    4. Enters the application's event loop.
    """
    # 1. Build the database and tables before the UI even thinks about loading
    init_db()

    # 2. Load application state from the database
    global_state.load_settings()

    # 3. Boot the UI
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
