from datetime import date

from sqlalchemy import Boolean, Column, Date, Float, Integer, String

from core.database import Base


class Income(Base):
    """SQLAlchemy model for storing income entries.

    This model defines the structure for income records in the database,
    including details such as the date, source, category, amount, and currency.
    """

    __tablename__ = "incomes"

    id: int = Column(Integer, primary_key=True, index=True)
    date: date = Column(Date, nullable=False)
    source: str = Column(String, nullable=False)
    category: str = Column(String, nullable=False)
    input_amount: float = Column(Float, nullable=False)
    currency: str = Column(String, nullable=False)
    amount_local: float = Column(Float, nullable=False)


class Asset(Base):
    """SQLAlchemy model for storing asset information.

    This model captures details about various assets, including their type,
    name, liquidity status, balance, currency, local value, and an optional
    external identifier for integration with external systems.
    """

    __tablename__ = "assets"

    id: int = Column(Integer, primary_key=True, index=True)
    asset_type: str = Column(String, nullable=False)
    asset_name: str = Column(String, nullable=False)
    is_liquid: bool = Column(Boolean, default=True)
    balance: float = Column(Float, nullable=False)
    currency: str = Column(String, nullable=False)
    value_local: float = Column(Float, nullable=False)
    external_id: str | None = Column(String, nullable=True)


class Bill(Base):
    """SQLAlchemy model for storing bill and expense information.

    This model defines the structure for recurring and one-time expenses,
    including their category, description, amount, currency, amount spent
    this month, frequency, and whether it's a fixed expense.
    """

    __tablename__ = "bills"

    id: int = Column(Integer, primary_key=True, index=True)
    category: str = Column(String, nullable=False)
    description: str | None = Column(String)
    amount: float = Column(Float, nullable=False)
    currency: str = Column(String, nullable=False)
    spent_this_month: float = Column(Float, default=0)
    frequency: str = Column(String, default="monthly")
    is_fixed: bool = Column(Boolean, default=True)


class Settings(Base):
    """SQLAlchemy model for storing application settings.

    This model holds global application settings, such as the user's
    preferred base currency and local currency, which are crucial for
    financial calculations and display.
    """

    __tablename__ = "settings"

    id: int = Column(Integer, primary_key=True, index=True)
    base_currency: str = Column(String, default="USD")
    local_currency: str = Column(String, default="PHP")
