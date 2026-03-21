from typing import Any, Dict, List, Optional

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

matplotlib.use("QtAgg")

# Modern Alchemist Color Palette (Adjust to match your exact QSS)
CHART_COLORS: list[str] = ["#00E676", "#D500F9", "#00B0FF", "#FFEA00", "#FF3D00"]
BG_COLOR: str = "none"  # Transparent to let PySide6 QSS show through
TEXT_COLOR: str = "#E0E0E0"


class DonutChartWidget(QWidget):
    """Reusable Donut Chart for tracking Income Sources or Asset Allocations.

    This widget displays data in a donut chart format using Matplotlib,
    embedded within a PySide6 application. It is designed to visualize
    proportional data, such as the distribution of income sources or
    asset categories.
    """

    def __init__(self, title: str = "Income Sources", parent: Optional[QWidget] = None) -> None:
        """Initializes the DonutChartWidget.

        Args:
            title: The title to display above the donut chart.
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
        self.title_text = title

        # Initial empty state
        self._setup_plot()

    def _setup_plot(self) -> None:
        """Configures the Matplotlib subplot for the donut chart.

        Clears the current axes, sets the aspect ratio to 'equal' for a circular
        pie, and adds the title text with appropriate styling for a dark theme.
        """
        self.ax.clear()
        self.ax.set_aspect("equal")
        self.figure.text(0.5, 0.9, self.title_text, ha="center", va="center", color=TEXT_COLOR, fontsize=12, fontweight="bold")

    def update_data(self, data: Dict[str, float]) -> None:
        """Updates the donut chart with new data.

        Takes a dictionary where keys are labels (e.g., income sources) and
        values are numerical amounts. It redraws the donut chart with the
        provided data, applying a predefined color palette and styling.
        If no data or zero sum is provided, it displays a "No Data" message.

        Args:
            data: A dictionary of {label: amount} to be visualized.
        """
        self._setup_plot()

        if not data or sum(data.values()) == 0:
            # Fallback for empty DB
            self.ax.pie([1], labels=["No Data"], colors=["#333333"],
                        wedgeprops=dict(width=0.3, edgecolor="#1E1E1E"))
            self.figure.tight_layout()
            self.canvas.draw()
            return

        labels: list[str] = list(data.keys())
        sizes: list[float] = list(data.values())

        # Donut specific props
        wedge_props: Dict[str, Any] = dict(width=0.4, edgecolor="#121212", linewidth=2)
        text_props: Dict[str, Any] = dict(color=TEXT_COLOR, fontsize=10)

        wedges, texts, autotexts = self.ax.pie(
            sizes,
            labels=labels,
            colors=CHART_COLORS[: len(labels)],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops=wedge_props,
            textprops=text_props,
            pctdistance=0.75,
        )

        # Style the percentage text
        for autotext in autotexts:
            autotext.set_color("#121212")
            autotext.set_fontweight("bold")

        self.figure.tight_layout()
        self.canvas.draw()
