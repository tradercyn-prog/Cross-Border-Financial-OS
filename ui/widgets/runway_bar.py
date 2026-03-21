from typing import List, Optional

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
from PySide6.QtWidgets import QVBoxLayout, QWidget

matplotlib.use("QtAgg")

# Modern Alchemist Color Palette (Adjust to match your exact QSS)
CHART_COLORS: List[str] = ["#00E676", "#D500F9", "#00B0FF", "#FFEA00", "#FF3D00"]
BG_COLOR: str = "none"  # Transparent to let PySide6 QSS show through
TEXT_COLOR: str = "#E0E0E0"


class RunwayBarWidget(QWidget):
    """Horizontal Bar Chart to visualize Safety Net / Runway in Months.

    This widget displays a horizontal bar representing the user's financial
    runway (how many months they can cover expenses with liquid assets).
    It compares the current runway against a target, using color coding
    to indicate status (red for low, yellow for medium, green for sufficient).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initializes the RunwayBarWidget.

        Args:
            parent: The parent QWidget for this widget.
        """
        super().__init__(parent)
        self.figure = Figure(facecolor=BG_COLOR)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color:transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.2, right=0.95, top=0.85, bottom=0.2)

        self._setup_plot()

    def _setup_plot(self) -> None:
        """Configures the Matplotlib subplot for the horizontal bar chart.

        Clears the current axes, sets the background to transparent, and
        styles the ticks and spines for a dark theme. It hides the top
        and right spines for a cleaner look.
        """
        self.ax.clear()
        self.ax.set_facecolor(BG_COLOR)
        self.ax.tick_params(colors=TEXT_COLOR)
        for spine in self.ax.spines.values():
            spine.set_edgecolor("#333333")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)

    def update_data(self, target_months: int, current_months: float) -> None:
        """Updates the runway bar with new target and current runway values.

        Draws a horizontal bar representing the current financial runway in
        months, with a background bar indicating the target. The bar's color
        changes based on how close the current runway is to the target.
        Major and minor ticks are set for monthly and weekly intervals.

        Args:
            target_months: The target number of months for the financial runway.
            current_months: The current calculated financial runway in months.
        """
        self._setup_plot()

        categories: List[str] = ["Runway"]

        # Background bar (Target)
        self.ax.barh(categories, [target_months], color="#1E1E1E", edgecolor="#333333", height=0.5)

        # Foreground bar (Actual)
        color: str = "#00E676" if current_months >= target_months else "#FFEA00"
        if current_months < (target_months * 0.25):
            color = "#FF3D00"

        self.ax.barh(categories, [current_months], color=color, height=0.5)

        self.ax.set_xlabel("Months of Living Expenses", color=TEXT_COLOR)

        # Stabilize X-axis
        x_max: float = max(12.0, float(target_months), current_months)
        self.ax.set_xlim(left=0, right=x_max)

        # Set monthly major ticks and weekly minor ticks
        self.ax.xaxis.set_major_locator(MultipleLocator(1))
        self.ax.xaxis.set_minor_locator(MultipleLocator(0.25))  # 4 weeks in a month
        self.ax.grid(which="minor", axis="x", linestyle=":", linewidth="0.5", color="#444444")
        self.ax.grid(which="major", axis="x", linestyle="-", linewidth="0.5", color="#666666")

        # Add text label above the bar
        self.ax.text(
            current_months * 0.5,
            0.3,
            f"{current_months:.1f} / {target_months} Mo",
            ha="center",
            va="bottom",
            color=TEXT_COLOR,
            fontweight="bold",
        )

        self.figure.text(0.5, 0.95, "Safety Net Status", ha="center", va="center", color=TEXT_COLOR, fontsize=12, fontweight="bold")

        self.figure.tight_layout()
        self.canvas.draw()
