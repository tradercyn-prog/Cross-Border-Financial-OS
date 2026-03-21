from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.calculations import FinancialEngine
from core.database import SessionLocal
from core.models import Asset, Bill, Income
from core.state import global_state
from integrations.exchange_rates import exchange_rate_provider
from ui.widgets.donut_chart import DonutChartWidget
from ui.widgets.flight_home_gauge import FlightHomeGaugeWidget
from ui.widgets.runway_bar import RunwayBarWidget
from ui.widgets.stat_card import StatCard


class DashboardTab(QWidget):
    """A QWidget tab displaying key financial metrics and visualizations.

    This tab provides an overview of the user's financial health, including
    net worth, liquid cash, burn rate, and dynamic spending goals. It integrates
    data from various sources and presents it through stat cards, charts, and gauges.
    """

    def __init__(self) -> None:
        """Initializes the DashboardTab.

        Sets up the user interface, initializes the dashboard with current data,
        and connects to the global state's data update signal to ensure real-time
        refreshing of displayed metrics.
        """
        super().__init__()
        self.init_ui()
        self.refresh_dashboard()

        # Listen for any data changes and refresh instantly
        global_state.data_updated.connect(self.refresh_dashboard)

    @staticmethod
    def get_color_from_percentage(percentage: float, invert: bool = False) -> str:
        """Determines a color based on a given percentage, transitioning from red to green.

        Args:
            percentage: A float between 0.0 and 1.0 representing the percentage.
            invert: If True, the color scale is inverted (green to red).

        Returns:
            A string representing a hex color code.
        """
        # Clamp the percentage between 0.0 and 1.0
        percentage = max(0.0, min(1.0, percentage))

        colors = ["#ff0000", "#ff4500", "#ff8c00", "#ffd700", "#adff2f", "#32cd32", "#00ff00"]

        if invert:
            colors.reverse()

        # Calculate the index
        index = int(percentage * (len(colors) - 1))

        return colors[index]

    def init_ui(self) -> None:
        """Initializes the user interface components for the Dashboard tab.

        This includes controls for pacing and safety net settings, various
        StatCard widgets to display key metrics, and custom widgets for
        donut charts, runway bars, and flight home gauges. These components
        are arranged using a grid layout.
        """
        self.main_layout = QVBoxLayout(self)

        # --- Pacing Toggle ---
        controls_layout = QHBoxLayout()
        self.pacing_label = QLabel("Enable Strict Weekly Pacing:")
        self.pacing_toggle = QComboBox()
        self.pacing_toggle.addItems(["No", "Yes"])
        self.pacing_toggle.currentTextChanged.connect(self.refresh_dashboard)
        controls_layout.addWidget(self.pacing_label)
        controls_layout.addWidget(self.pacing_toggle)

        self.safety_net_label = QLabel("Safety Net (Months):")
        self.safety_net_spinbox = QSpinBox()
        self.safety_net_spinbox.setRange(0, 12)
        self.safety_net_spinbox.setValue(0)
        self.safety_net_spinbox.valueChanged.connect(self.refresh_dashboard)

        controls_layout.addWidget(self.safety_net_label)
        controls_layout.addWidget(self.safety_net_spinbox)
        controls_layout.addStretch()

        self.main_layout.addLayout(controls_layout)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)

        # --- Stat Cards ---
        self.fx_rate_card = StatCard(f"{global_state.base_currency} to {global_state.local_currency} Exchange Rate")
        self.safe_to_spend_card = StatCard("Safe to Spend")
        self.safe_to_spend_sparkline = QProgressBar()
        self.safe_to_spend_sparkline.setFixedHeight(4)
        self.safe_to_spend_sparkline.setTextVisible(False)
        safe_to_spend_layout = QVBoxLayout()
        safe_to_spend_layout.addWidget(self.safe_to_spend_card)
        safe_to_spend_layout.addWidget(self.safe_to_spend_sparkline)
        safe_to_spend_layout.setSpacing(0)
        self.burn_rate_card = StatCard("Remaining Monthly Burn")
        self.liquid_card = StatCard(f"Liquid Cash ({global_state.base_currency})")
        self.net_worth_card = StatCard(f"Total Net Worth ({global_state.base_currency})")
        self.daily_target_card = StatCard("Dynamic Daily Target")
        self.daily_target_sparkline = QProgressBar()
        self.daily_target_sparkline.setFixedHeight(4)
        self.daily_target_sparkline.setTextVisible(False)
        daily_target_layout = QVBoxLayout()
        daily_target_layout.addWidget(self.daily_target_card)
        daily_target_layout.addWidget(self.daily_target_sparkline)
        daily_target_layout.setSpacing(0)
        self.weekly_target_card = StatCard("Remaining Weekly Target")
        self.weekly_target_sparkline = QProgressBar()
        self.weekly_target_sparkline.setFixedHeight(4)
        self.weekly_target_sparkline.setTextVisible(False)
        weekly_target_layout = QVBoxLayout()
        weekly_target_layout.addWidget(self.weekly_target_card)
        weekly_target_layout.addWidget(self.weekly_target_sparkline)
        weekly_target_layout.setSpacing(0)
        self.total_monthly_earned_card = StatCard("Total Monthly Earned")
        self.total_monthly_earned_sparkline = QProgressBar()
        self.total_monthly_earned_sparkline.setFixedHeight(4)
        self.total_monthly_earned_sparkline.setTextVisible(False)
        total_monthly_earned_layout = QVBoxLayout()
        total_monthly_earned_layout.addWidget(self.total_monthly_earned_card)
        total_monthly_earned_layout.addWidget(self.total_monthly_earned_sparkline)
        total_monthly_earned_layout.setSpacing(0)

        # --- Charts ---
        self.income_donut = DonutChartWidget(title="Income Sources")
        self.flight_home_gauge = FlightHomeGaugeWidget()
        self.runway_bar = RunwayBarWidget()

        # --- Layout ---

        # Row 0
        self.grid_layout.addWidget(self.fx_rate_card, 0, 0, 1, 2)
        self.grid_layout.addLayout(safe_to_spend_layout, 0, 2, 1, 2)
        self.grid_layout.addWidget(self.burn_rate_card, 0, 4, 1, 2)

        # Row 1
        self.grid_layout.addWidget(self.liquid_card, 1, 0, alignment=Qt.AlignCenter)

        chart_layout = QHBoxLayout()
        chart_layout.addWidget(self.income_donut)
        chart_layout.addWidget(self.flight_home_gauge)
        chart_layout.addWidget(self.runway_bar)
        self.grid_layout.addLayout(chart_layout, 1, 1, 1, 4)

        self.grid_layout.addWidget(self.net_worth_card, 1, 5, alignment=Qt.AlignCenter)

        # Row 2
        self.grid_layout.addLayout(daily_target_layout, 2, 0, 1, 2)
        self.grid_layout.addLayout(weekly_target_layout, 2, 2, 1, 2)
        self.grid_layout.addLayout(total_monthly_earned_layout, 2, 4, 1, 2)

        self.grid_layout.setRowMinimumHeight(1, 250)  # Give charts space

        self.main_layout.addLayout(self.grid_layout)
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    @Slot()
    def refresh_dashboard(self) -> None:
        """Refreshes all financial metrics and visualizations on the dashboard.

        This method fetches the latest data from the database, calculates
        various financial indicators using the FinancialEngine, and updates
        the UI elements accordingly. It also applies conditional formatting
        and updates sparklines based on the calculated metrics.
        """
        engine = FinancialEngine()
        with SessionLocal() as session:
            incomes: List[Dict[str, Any]] = [{k: v for k, v in row.__dict__.items() if not k.startswith("_")} for row in session.query(Income).all()]
            bills: List[Dict[str, Any]] = [{k: v for k, v in row.__dict__.items() if not k.startswith("_")} for row in session.query(Bill).all()]
            assets: List[Dict[str, Any]] = [{k: v for k, v in row.__dict__.items() if not k.startswith("_")} for row in session.query(Asset).all()]

        now = datetime.now()
        fx_rate: Optional[float] = exchange_rate_provider.get_live_rate(global_state.base_currency, global_state.local_currency)
        safety_net_months: int = self.safety_net_spinbox.value()
        pacing_enabled: bool = self.pacing_toggle.currentText() == "Yes"

        base_currency_symbol: str = global_state.currency_symbols.get(global_state.base_currency, global_state.base_currency)

        # Update titles to reflect current global state
        self.fx_rate_card.title_label.setText(f"{global_state.base_currency} to {global_state.local_currency} Exchange Rate")
        self.liquid_card.title_label.setText(f"Liquid Cash ({global_state.base_currency})")
        self.net_worth_card.title_label.setText(f"Total Net Worth ({global_state.base_currency})")

        if fx_rate is not None:
            self.fx_rate_card.update_value(f"{fx_rate:.4f}")
        else:
            self.fx_rate_card.update_value("N/A")
            fx_rate = 58.0  # Fallback rate

        net_worth, liquid_net_worth = engine.calculate_net_worth(assets, fx_rate)
        global_state.set_metric("liquid_net_worth", liquid_net_worth)

        gross_monthly_burn, total_spent_this_month = engine.calculate_burn_rate(bills, fx_rate)

        dashboard_metrics: Dict[str, float] = engine.get_dashboard_metrics(
            liquid_base=liquid_net_worth,
            gross_monthly_burn_base=gross_monthly_burn,
            total_spent_this_month_base=total_spent_this_month,
            safety_net_months=float(safety_net_months),
            pacing_enabled=pacing_enabled,
            income_data=incomes,
            exchange_rate=fx_rate,
            current_date=now.date(),
        )

        self.net_worth_card.update_value(f"{base_currency_symbol}{net_worth:,.2f}")
        self.liquid_card.update_value(f"{base_currency_symbol}{liquid_net_worth:,.2f}")
        self.burn_rate_card.update_value(f"{base_currency_symbol}{dashboard_metrics['remaining_monthly_burn_base']:,.2f}")
        self.safe_to_spend_card.update_value(f"{base_currency_symbol}{dashboard_metrics['safe_to_spend']:,.2f}")
        self.daily_target_card.update_value(f"{base_currency_symbol}{dashboard_metrics[f'daily_hustle_{global_state.base_currency.lower()}']:,.2f}")
        self.weekly_target_card.update_value(f"{base_currency_symbol}{dashboard_metrics[f'remaining_weekly_target_{global_state.base_currency.lower()}']:,.2f}")
        self.total_monthly_earned_card.update_value(f"{base_currency_symbol}{dashboard_metrics[f'total_earned_{global_state.base_currency.lower()}']:.2f}")

        income_sources: Dict[str, float] = engine.get_income_sources(incomes, fx_rate)
        self.income_donut.update_data(income_sources)

        # Update flight home gauge
        flight_home_target: float = 1500.00
        self.flight_home_gauge.update_data(liquid_cash=liquid_net_worth, target=flight_home_target)

        # Update runway bar with actual data
        current_runway_months: float = liquid_net_worth / gross_monthly_burn if gross_monthly_burn > 0 else 0
        self.runway_bar.update_data(target_months=safety_net_months, current_months=current_runway_months)

        # --- Conditional Formatting & Sparklines ---

        # Remaining Weekly Target
        remaining_weekly: float = dashboard_metrics.get(f"remaining_weekly_target_{global_state.base_currency.lower()}", 0.0)
        gross_weekly: float = dashboard_metrics.get(f"gross_weekly_target_{global_state.base_currency.lower()}", 0.0)

        if gross_weekly > 0:
            # A higher remaining target is worse, so we want the percentage to reflect that for the color scale.
            # If remaining is high, percentage is high -> red color (with invert=True).
            percent_remaining: float = remaining_weekly / gross_weekly
        else:
            percent_remaining = 0.0

        # We want the BAR to show progress, so we show (1 - remaining)%
        progress_percent: float = max(0.0, 1.0 - percent_remaining)

        # Color is based on how much is remaining (bad), so use percent_remaining
        color_remaining: str = self.get_color_from_percentage(percent_remaining, invert=True)
        self.weekly_target_card.value_label.setStyleSheet(f"color: {color_remaining}; font-size: 26px; font-weight: bold;")
        self.weekly_target_sparkline.setValue(int(progress_percent * 100))
        self.weekly_target_sparkline.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color_remaining}; }}")

        # Safe to Spend
        safe_to_spend: float = dashboard_metrics.get("safe_to_spend", 0.0)

        if safe_to_spend < 0:
            color_safe: str = "#ff0000"
            percent_safe_for_bar: int = 100
        else:
            baseline: float = gross_monthly_burn
            if baseline > 0:
                percent_safe: float = safe_to_spend / baseline
            else:
                percent_safe = 1.0  # If no burn, any spending is safe, so 100%

            percent_safe = min(1.0, percent_safe)  # Cap at 100% for the visual
            color_safe = self.get_color_from_percentage(percent_safe, invert=False)
            percent_safe_for_bar = int(percent_safe * 100)

        self.safe_to_spend_card.value_label.setStyleSheet(f"color: {color_safe}; font-size: 26px; font-weight: bold;")
        self.safe_to_spend_sparkline.setValue(percent_safe_for_bar)
        self.safe_to_spend_sparkline.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color_safe}; }}")

        # Daily Target
        earned_today: float = dashboard_metrics.get(f"earned_today_{global_state.base_currency.lower()}", 0.0)
        daily_target: float = dashboard_metrics.get(f"daily_hustle_{global_state.base_currency.lower()}", 0.0)

        if daily_target > 0:
            percent_daily: float = min(1.0, earned_today / daily_target)
        else:
            percent_daily = 1.0  # If no target, 100%

        color_daily: str = self.get_color_from_percentage(percent_daily, invert=False)
        self.daily_target_card.value_label.setStyleSheet(f"color: {color_daily}; font-size: 26px; font-weight: bold;")
        self.daily_target_sparkline.setValue(int(percent_daily * 100))
        self.daily_target_sparkline.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color_daily}; }}")

        # Monthly Target
        total_earned: float = dashboard_metrics.get(f"total_earned_{global_state.base_currency.lower()}", 0.0)
        monthly_target: float = gross_monthly_burn  # gross_monthly_burn_base

        if monthly_target > 0:
            percent_monthly: float = min(1.0, total_earned / monthly_target)
        else:
            percent_monthly = 1.0

        color_monthly: str = self.get_color_from_percentage(percent_monthly, invert=False)
        self.total_monthly_earned_card.value_label.setStyleSheet(f"color: {color_monthly}; font-size: 26px; font-weight: bold;")
        self.total_monthly_earned_sparkline.setValue(int(percent_monthly * 100))
        self.total_monthly_earned_sparkline.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color_monthly}; }}")
