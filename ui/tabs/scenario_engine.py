from typing import List, Optional
import logging

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QSpacerItem,
)

from core.state import global_state
from integrations.exchange_rates import exchange_rate_provider


class ScenarioEngineTab(QWidget):
    """A QWidget tab for simulating financial scenarios and visualizing their impact.

    This tab allows users to input hypothetical monthly costs and local currencies
    to calculate a 'scenario runway' in months. It compares this scenario against
    the user's actual financial runway and visualizes the comparison using a chart.
    It also integrates with the Wise API to fetch live exchange rates.
    """

    def __init__(self) -> None:
        """Initializes the ScenarioEngineTab.

        Sets up the user interface, connects signals to slots for interactive
        updates, and performs an initial update of the readouts and chart.
        It also connects to the global state's data update signal.
        """
        super().__init__()
        self.init_ui()
        self.connect_signals()
        self.update_readouts()

        global_state.data_updated.connect(self.update_readouts)

    def init_ui(self) -> None:
        """Initializes the user interface components for the Scenario Engine tab.

        This includes input fields for target country, estimated monthly cost,
        local currency, and FX rate. It also features readouts for current
        liquid cash, scenario monthly burn, and scenario runway, along with
        a Matplotlib chart for visual comparison.
        """
        self.main_layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)

        # --- Left Column (Inputs) ---
        self.target_country_label = QLabel("Target Country:")
        self.target_country_input = QComboBox()
        self.target_country_input.setEditable(True)
        self.target_country_input.addItems(["Japan", "USA", "Canada", "Australia"])

        self.monthly_cost_label = QLabel("Estimated Monthly Cost (Local Currency):")
        self.monthly_cost_input = QLineEdit()
        self.monthly_cost_input.setValidator(QDoubleValidator(0.0, 1000000000.0, 2))

        self.local_currency_label = QLabel("Local Currency:")
        self.local_currency_input = QComboBox()
        self.local_currency_input.setEditable(True)
        self.local_currency_input.addItems(["JPY", "USD", "CAD", "AUD", "PHP"])

        self.fx_rate_label = QLabel("Live FX Rate to USD:")
        self.fx_rate_input = QLineEdit()
        self.fx_rate_input.setValidator(QDoubleValidator(0.0, 1000000.0, 6))
        self.fetch_fx_button = QPushButton("Fetch from Wise")

        input_layout = QVBoxLayout()
        input_layout.addWidget(self.target_country_label)
        input_layout.addWidget(self.target_country_input)
        input_layout.addWidget(self.monthly_cost_label)
        input_layout.addWidget(self.monthly_cost_input)
        input_layout.addWidget(self.local_currency_label)
        input_layout.addWidget(self.local_currency_input)

        fx_layout = QHBoxLayout()
        fx_layout.addWidget(self.fx_rate_input)
        fx_layout.addWidget(self.fetch_fx_button)

        input_layout.addWidget(self.fx_rate_label)
        input_layout.addLayout(fx_layout)
        input_layout.addStretch()

        # --- Right Column (Readouts) ---
        self.liquid_cash_label = QLabel("Current Liquid Cash (USD):")
        self.liquid_cash_value = QLabel("$0.00")
        self.liquid_cash_value.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.monthly_burn_label = QLabel("Scenario Monthly Burn (USD):")
        self.monthly_burn_value = QLabel("$0.00")
        self.monthly_burn_value.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff4500;")

        self.runway_label = QLabel("Scenario Runway (Months):")
        self.runway_value = QLabel("0.0")
        self.runway_value.setStyleSheet("font-size: 18px; font-weight: bold; color: #32cd32;")

        readout_layout = QVBoxLayout()
        readout_layout.addWidget(self.liquid_cash_label)
        readout_layout.addWidget(self.liquid_cash_value)
        readout_layout.addSpacing(15)
        readout_layout.addWidget(self.monthly_burn_label)
        readout_layout.addWidget(self.monthly_burn_value)
        readout_layout.addSpacing(15)
        readout_layout.addWidget(self.runway_label)
        readout_layout.addWidget(self.runway_value)
        readout_layout.addStretch()

        # --- Bottom Span (Visual) ---
        self.fig = Figure(figsize=(5, 2), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        # --- Layout Assembly ---
        self.grid_layout.addLayout(input_layout, 0, 0)
        self.grid_layout.addLayout(readout_layout, 0, 1)
        self.grid_layout.addWidget(self.canvas, 1, 0, 1, 2)

        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)

        self.main_layout.addLayout(self.grid_layout)
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def connect_signals(self) -> None:
        """Connects UI element signals to their respective slots.

        Ensures that changes in input fields or button clicks trigger the
        appropriate update or fetch operations.
        """
        self.monthly_cost_input.textChanged.connect(self.update_readouts)
        self.fx_rate_input.textChanged.connect(self.update_readouts)
        self.fetch_fx_button.clicked.connect(self.fetch_fx_rate)
        self.local_currency_input.currentTextChanged.connect(self.on_currency_change)

    def on_currency_change(self) -> None:
        """Clears the FX rate input and updates readouts when the local currency changes.

        This ensures that the user is prompted to fetch a new FX rate relevant
        to the newly selected local currency.
        """
        self.fx_rate_input.clear()
        self.update_readouts()

    def fetch_fx_rate(self) -> None:
        """Fetches the live exchange rate from Wise.com and updates the FX rate input field.

        The exchange rate is fetched between the currently selected local currency
        and the global base currency (USD). The fetched rate is then displayed
        in the FX rate input field, and the readouts are updated.
        """
        target_currency: str = self.local_currency_input.currentText()
        base_currency: str = global_state.base_currency
        if not target_currency:
            return

        try:
            rate: Optional[float] = exchange_rate_provider.wise_client.get_exchange_rate(source=target_currency, target=base_currency)
            if isinstance(rate, float):
                self.fx_rate_input.setText(f"{rate:.6f}")
                self.update_readouts()
            else:
                self.fx_rate_input.setText("N/A")
        except Exception as e:
            logging.error(f"Could not fetch rate: {e}")
            self.fx_rate_input.setText("Error")

    def update_readouts(self) -> None:
        """Updates all scenario-related financial readouts and the comparison chart.

        This method retrieves user inputs for monthly cost and FX rate,
        fetches the current liquid cash from the global state, performs
        calculations for scenario monthly burn and runway, and then updates
        the corresponding QLabel widgets and the Matplotlib chart.
        """
        # --- Get Inputs ---
        try:
            monthly_cost_local: float = float(self.monthly_cost_input.text()) if self.monthly_cost_input.text() else 0.0
            fx_rate_to_usd: float = float(self.fx_rate_input.text()) if self.fx_rate_input.text() else 0.0
        except (ValueError, TypeError):
            monthly_cost_local = 0.0
            fx_rate_to_usd = 0.0

        # --- Get Global State ---
        liquid_cash_usd: float = global_state.get_metric("liquid_net_worth") or 0.0
        safety_net_months: float = global_state.get_metric("safety_net_months") or 3.0  # Assuming a default if not set

        # --- Calculations ---
        monthly_burn_usd: float = monthly_cost_local * fx_rate_to_usd
        runway_months: float = liquid_cash_usd / monthly_burn_usd if monthly_burn_usd > 0 else 0.0

        # --- Update Readouts ---
        self.liquid_cash_value.setText(f"${liquid_cash_usd:,.2f}")
        self.monthly_burn_value.setText(f"${monthly_burn_usd:,.2f}")
        self.runway_value.setText(f"{runway_months:.1f} months")

        self.update_chart(runway_months, safety_net_months)

    def update_chart(self, scenario_runway: float, safety_net_months: float) -> None:
        """Updates the Matplotlib bar chart comparing current and scenario runways.

        The chart visualizes the user's current financial runway (from global state)
        against the simulated scenario runway. It also includes a vertical line
        indicating the target safety net in months. The chart is styled for a
        dark theme.

        Args:
            scenario_runway: The calculated financial runway for the current scenario in months.
            safety_net_months: The target safety net in months, retrieved from global state.
        """
        self.ax.clear()

        # Dark Mode Styling
        self.fig.patch.set_facecolor("#1e1e1e")
        self.ax.set_facecolor("#1e1e1e")

        self.ax.spines["bottom"].set_color("white")
        self.ax.spines["top"].set_color("white")
        self.ax.spines["right"].set_color("white")
        self.ax.spines["left"].set_color("white")

        self.ax.tick_params(axis="x", colors="white")
        self.ax.tick_params(axis="y", colors="white")

        self.ax.yaxis.label.set_color("white")
        self.ax.xaxis.label.set_color("white")

        # --- Get Data ---
        # Placeholder for home runway and safety net
        home_runway_months: float = global_state.get_metric("runway_months") or 0.0

        labels: List[str] = [f"Runway (Home/{global_state.local_currency})", "Runway (Scenario)"]
        values: List[float] = [home_runway_months, scenario_runway]

        bars = self.ax.barh(labels, values, color=["#1f77b4", "#ff7f0e"])
        self.ax.set_xlabel("Months", color="white")
        title = self.ax.set_title("Runway Comparison")
        title.set_color("white")
        max_val: float = max(values) if values else 0.0
        self.ax.set_xlim(0, max_val * 1.15)

        # Add Safety Net Threshold line
        self.ax.axvline(x=safety_net_months, color="r", linestyle="--", linewidth=2, label=f"Safety Net ({safety_net_months} mos)")

        # Add value labels on bars
        for bar in bars:
            width: float = bar.get_width()
            self.ax.text(
                width + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{width:.1f}",
                ha="left",
                va="center",
                color="white",
            )

        legend = self.ax.legend()
        for text in legend.get_texts():
            text.set_color("white")

        self.fig.tight_layout()
        self.canvas.draw()
