from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from .tabs.assets_tracker import AssetsTrackerTab
from .tabs.bills_planner import BillsPlannerTab
from .tabs.dashboard import DashboardTab
from .tabs.data_connection import DataConnectionTab
from .tabs.income_logger import IncomeLoggerTab
from .tabs.scenario_engine import ScenarioEngineTab
from .tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """The main application window for the Cross-Border Financial OS.

    This window serves as the primary container for all other UI components,
    organizing them into a tabbed interface. It sets up the main window
    properties like title, size, and applies a dark theme.
    """

    def __init__(self) -> None:
        """Initializes the MainWindow.

        Sets up the window title, size, and applies a dark stylesheet.
        It then initializes the QTabWidget and adds all the application's
        functional tabs to it.
        """
        super().__init__()

        self.setWindowTitle("Cross-Border Financial OS")
        self.resize(1200, 800)

        # Apply a dark theme
        self.setStyleSheet("background-color: #2B2B2B;")

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.dashboard_tab = DashboardTab()
        self.income_logger_tab = IncomeLoggerTab()
        self.bills_planner_tab = BillsPlannerTab()
        self.assets_tracker_tab = AssetsTrackerTab()
        self.data_connection_tab = DataConnectionTab()
        self.scenario_engine_tab = ScenarioEngineTab()
        self.settings_tab = SettingsTab()

        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.income_logger_tab, "Income Logger")
        self.tab_widget.addTab(self.bills_planner_tab, "Bills Planner")
        self.tab_widget.addTab(self.assets_tracker_tab, "Assets")
        self.tab_widget.addTab(self.data_connection_tab, "Data Connection")
        self.tab_widget.addTab(self.scenario_engine_tab, "Next Stop")
        self.tab_widget.addTab(self.settings_tab, "Settings")
