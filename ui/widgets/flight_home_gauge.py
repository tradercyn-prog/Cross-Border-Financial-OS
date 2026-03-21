from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

matplotlib.use("QtAgg")

# Modern Alchemist Color Palette
BG_COLOR: str = "none"  # Transparent
TEXT_COLOR: str = "#E0E0E0"


class FlightHomeGaugeWidget(QWidget):
    """A horizontal progress bar to visualize the 'Emergency Flight Home' fund.

    This widget displays the progress towards a financial target (e.g., an
    emergency fund for a flight home) using a horizontal bar chart. The color
    of the bar changes based on the percentage of the target achieved.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initializes the FlightHomeGaugeWidget.

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
        self.figure.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.4)

        self._setup_plot()

    def _setup_plot(self) -> None:
        """Configures the Matplotlib subplot for the horizontal gauge.

        Clears the current axes, sets the background to transparent, and
        styles the ticks and spines for a dark theme. It also hides the
        Y-axis labels as they are not relevant for a horizontal gauge.
        """
        self.ax.clear()
        self.ax.set_facecolor(BG_COLOR)
        self.ax.tick_params(colors=TEXT_COLOR, labelsize=10)
        for spine in self.ax.spines.values():
            spine.set_edgecolor("#333333")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_visible(False)  # Hide Y-axis spine

        # Hide Y-axis labels
        self.ax.yaxis.set_major_formatter(plt.NullFormatter())
        self.ax.yaxis.set_ticks([])

    def update_data(self, liquid_cash: float, target: float) -> None:
        """Updates the progress bar with new liquid cash and target values.

        Calculates the percentage progress towards the target and updates the
        horizontal bar chart. The color of the bar changes dynamically based
        on the progress (red for low, yellow for medium, green for high).
        Displays the current liquid cash and target values as text.

        Args:
            liquid_cash: The current amount of liquid cash available.
            target: The financial target for the emergency fund.
        """
        self._setup_plot()

        # Prevent division by zero
        if target == 0:
            progress_percent: float = 0.0
        else:
            progress_percent = (liquid_cash / target) * 100

        # Determine color based on progress
        if liquid_cash >= target:
            color: str = "#00E676"  # Green
        elif liquid_cash >= target * 0.5:
            color = "#FFEA00"  # Yellow
        else:
            color = "#FF3D00"  # Red

        # Background bar (Target)
        self.ax.barh([0], [100], color="#1E1E1E", edgecolor="#333333", height=0.5)

        # Foreground bar (Actual)
        self.ax.barh([0], [min(progress_percent, 100)], color=color, height=0.5)

        self.ax.set_xlabel("Progress (%)", color=TEXT_COLOR, fontsize=10)
        self.ax.set_xlim(0, 100)

        # Add text label
        label: str = f"${liquid_cash:,.0f} / ${target:,.0f}"
        self.ax.text(50, 0, label, ha="center", va="center", color="#121212", fontweight="bold", fontsize=12)

        self.figure.text(0.5, 0.95, "Emergency Flight Home", ha="center", va="center", color=TEXT_COLOR, fontsize=12, fontweight="bold")

        self.figure.tight_layout()
        self.canvas.draw()
