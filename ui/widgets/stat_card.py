from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    """A reusable QFrame widget designed to display a title and a value, typically for financial metrics.

    This widget provides a visually distinct card-like container for displaying
    key statistics on a dashboard. It includes styling for the title and value
    labels, and supports dynamic updates of the displayed value.
    """

    def __init__(self, title: str, value: str = "$0.00", parent: Optional[QFrame] = None) -> None:
        """Initializes the StatCard.

        Args:
            title: The title text to display on the card.
            value: The initial value text to display on the card.
            parent: The parent QFrame for this widget.
        """
        super().__init__(parent)

        # THIS IS REQUIRED FOR THE CSS TO ATTACH
        self.setObjectName("StatCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(15, 15, 15, 15)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("StatTitle")
        self.title_label.setAlignment(Qt.AlignLeft)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        self.value_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

        self.setStyleSheet(
            """
            QFrame#StatCard {
                background-color: #0D0D0F;
                border: 1px solid #4A4A5A;
                border-radius: 4px;
            }
            QLabel#StatTitle {
                background-color: transparent;
                color: #8B7D9B;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
            }
            QLabel#StatValue {
                background-color: transparent;
                color: #E2E8F0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 26px;
                font-weight: bold;
            }
        """
        )

    def update_value(self, new_value: str) -> None:
        """Updates the displayed value on the StatCard.

        Args:
            new_value: The new string value to display on the card.
        """
        self.value_label.setText(new_value)
