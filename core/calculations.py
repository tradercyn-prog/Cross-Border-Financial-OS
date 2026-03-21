import calendar
import datetime
from typing import Dict, List, Tuple

import polars as pl

from core.state import global_state


class FinancialEngine:
    """Provides the analytical core for financial calculations using Polars.

    This class encapsulates financial logic, including net worth calculation,
    burn rate analysis, and dynamic goal setting, leveraging the Polars
    dataframe library for efficient data manipulation. It operates with
    a base currency and a local currency, performing necessary conversions
    using provided exchange rates.
    """

    def __init__(self) -> None:
        """Initializes the FinancialEngine with global currency settings.

        The base and local currencies are retrieved from the global_state
        object, which is expected to be initialized elsewhere in the application.
        """
        self.base_currency: str = global_state.base_currency
        self.local_currency: str = global_state.local_currency

    def _normalize_to_base(self, df: pl.DataFrame, amount_col: str, exchange_rate: float) -> pl.DataFrame:
        """Normalizes a specified amount column in a DataFrame to the base currency.

        This private helper method converts amounts from the local currency to the
        base currency using the provided exchange rate. If the currency in the
        DataFrame row is already the base currency, no conversion is applied.

        Args:
            df: The Polars DataFrame containing financial data, including 'currency'
                and the specified 'amount_col'.
            amount_col: The name of the column in the DataFrame that contains
                the amount to be normalized.
            exchange_rate: The exchange rate to convert from the local currency
                to the base currency.

        Returns:
            A new Polars DataFrame with an additional column named
            '{amount_col}_{base_currency.lower()}' containing the normalized amounts.
        """
        return df.with_columns(
            pl.when(pl.col("currency") == self.local_currency)
            .then(pl.col(amount_col) / exchange_rate)
            .otherwise(pl.col(amount_col))
            .alias(f"{amount_col}_{self.base_currency.lower()}")
        )

    def calculate_net_worth(self, assets_data: List[Dict], exchange_rate: float) -> Tuple[float, float]:
        """Calculates the total net worth and liquid cash from asset data.

        This method processes a list of asset dictionaries, normalizes their
        balances to the base currency, and then sums them to determine the
        total net worth and the portion that is liquid cash.

        Args:
            assets_data: A list of dictionaries, where each dictionary represents
                an asset and contains keys like 'balance', 'currency', and 'is_liquid'.
            exchange_rate: The exchange rate to convert from the local currency
                to the base currency.

        Returns:
            A tuple containing two floats: (total_net_worth_in_base_currency,
            liquid_cash_in_base_currency). Returns (0.0, 0.0) if no asset data is provided.
        """
        if not assets_data:
            return 0.0, 0.0

        df = pl.DataFrame(assets_data)
        df = self._normalize_to_base(df, "balance", exchange_rate)

        total_net_worth = df[f"balance_{self.base_currency.lower()}"].sum()
        liquid_cash = df.filter(pl.col("is_liquid") == True)[f"balance_{self.base_currency.lower()}"].sum()

        return float(total_net_worth or 0.0), float(liquid_cash or 0.0)

    def calculate_burn_rate(self, bills_data: List[Dict], exchange_rate: float) -> Tuple[float, float]:
        """Calculates gross monthly burn and total spent this month from bill data.

        This method takes a list of bill dictionaries, normalizes amounts to the
        base currency, and then prorates recurring bills to a monthly equivalent
        to determine the gross monthly burn rate. It also calculates the total
        amount spent this month.

        Args:
            bills_data: A list of dictionaries, where each dictionary represents
                a bill and contains keys like 'amount', 'currency', 'frequency',
                and 'spent_this_month'.
            exchange_rate: The exchange rate to convert from the local currency
                to the base currency.

        Returns:
            A tuple containing two floats: (gross_monthly_burn_in_base_currency,
            total_spent_this_month_in_base_currency). Returns (0.0, 0.0) if no
            bill data is provided.
        """
        if not bills_data:
            return 0.0, 0.0

        df = pl.DataFrame(bills_data)
        df = self._normalize_to_base(df, "amount", exchange_rate)
        df = self._normalize_to_base(df, "spent_this_month", exchange_rate)

        # Get total spent before it's prorated
        total_spent_this_month_base = df[f"spent_this_month_{self.base_currency.lower()}"].sum()

        # Normalize frequency to a strict Monthly rate
        df = df.with_columns(
            pl.col("frequency").str.to_lowercase().str.strip_chars().alias("frequency_normalized")
        ).with_columns(
            pl.when(pl.col("frequency_normalized") == "weekly")
            .then(pl.col(f"amount_{self.base_currency.lower()}") * (52.0 / 12.0))
            .when((pl.col("frequency_normalized") == "bi-weekly") | (pl.col("frequency_normalized") == "biweekly"))
            .then(pl.col(f"amount_{self.base_currency.lower()}") * (26.0 / 12.0))
            .when(pl.col("frequency_normalized") == "monthly")
            .then(pl.col(f"amount_{self.base_currency.lower()}"))
            .when(pl.col("frequency_normalized") == "quarterly")
            .then(pl.col(f"amount_{self.base_currency.lower()}") / 3.0)
            .when((pl.col("frequency_normalized") == "annually") | (pl.col("frequency_normalized") == "yearly"))
            .then(pl.col(f"amount_{self.base_currency.lower()}") / 12.0)
            .otherwise(pl.col(f"amount_{self.base_currency.lower()}"))
            .alias(f"monthly_burn_{self.base_currency.lower()}")
        )

        gross_monthly_burn_base = df[f"monthly_burn_{self.base_currency.lower()}"].sum()

        return float(gross_monthly_burn_base or 0.0), float(total_spent_this_month_base or 0.0)

    def calculate_pacing_multiplier(self, current_day: int) -> float:
        """Calculates a pacing multiplier based on the current day of the month.

        This multiplier is used to adjust financial goals dynamically throughout
        the month, providing a progressive target based on how far into the month it is.

        Args:
            current_day: An integer representing the current day of the month (1-31).

        Returns:
            A float representing the pacing multiplier.
        """
        if 1 <= current_day <= 7:
            return 0.25
        elif 8 <= current_day <= 14:
            return 0.50
        elif 15 <= current_day <= 21:
            return 0.75
        else:
            return 1.0

    def calculate_dynamic_goals(
        self,
        gross_monthly_burn_base: float,
        total_spent_this_month_base: float,
        income_data: List[Dict],
        exchange_rate: float,
        liquid_base: float,
        target_safety_net_months: float,
        pacing_enabled: bool,
        current_date: datetime.date = None,
    ) -> Dict[str, float]:
        """Calculates various dynamic financial goals and metrics for the dashboard.

        This comprehensive method computes metrics such as safe-to-spend, remaining
        monthly burn, daily hustle goals, and weekly targets, taking into account
        pacing, safety net deficits, and income data.

        Args:
            gross_monthly_burn_base: The total estimated monthly expenses in the base currency.
            total_spent_this_month_base: The total amount already spent this month in the base currency.
            income_data: A list of dictionaries, where each dictionary represents
                an income entry and contains keys like 'input_amount', 'currency', and 'date'.
            exchange_rate: The exchange rate to convert from the local currency
                to the base currency.
            liquid_base: The current amount of liquid cash available in the base currency.
            target_safety_net_months: The desired number of months of gross burn
                to keep as a safety net.
            pacing_enabled: A boolean indicating whether daily/weekly pacing
                should be applied to goals.
            current_date: An optional datetime.date object representing the current date.
                Defaults to today's date if not provided.

        Returns:
            A dictionary containing various calculated financial metrics, such as:
            - 'safe_to_spend': The amount of liquid cash safe to spend.
            - 'remaining_monthly_burn_base': Remaining monthly expenses.
            - 'total_spent_this_month_base': Total spent this month.
            - 'monthly_target_{base_currency.lower()}': Gross monthly burn target.
            - 'remaining_to_earn_{base_currency.lower()}': Remaining income needed.
            - 'daily_hustle_{base_currency.lower()}': Daily income goal.
            - 'gross_weekly_target_{base_currency.lower()}': Gross weekly income target.
            - 'remaining_weekly_target_{base_currency.lower()}': Remaining weekly income target.
            - 'total_earned_{base_currency.lower()}': Total income earned.
            - 'earned_today_{base_currency.lower()}': Income earned today.
        """
        if current_date is None:
            current_date = datetime.date.today()

        # 0. Calculate the Safety Net Deficit (based on GROSS burn)
        target_safety_net_cash = gross_monthly_burn_base * target_safety_net_months
        safety_net_deficit = max(0.0, target_safety_net_cash - liquid_base)

        # 1. Envelope Math Fix (New Logic)
        remaining_monthly_burn_base = max(0.0, gross_monthly_burn_base - total_spent_this_month_base)

        if pacing_enabled:
            pacing_ratio = self.calculate_pacing_multiplier(current_date.day)
            paced_burn = gross_monthly_burn_base * pacing_ratio
            target_cash_needed = max(0.0, paced_burn - total_spent_this_month_base) + safety_net_deficit
        else:
            target_cash_needed = remaining_monthly_burn_base + safety_net_deficit

        safe_to_spend = liquid_base - target_cash_needed

        # 2. Time boundary calculations
        start_of_week = current_date - datetime.timedelta(days=current_date.weekday())
        _, last_day = calendar.monthrange(current_date.year, current_date.month)
        end_of_month = datetime.date(current_date.year, current_date.month, last_day)

        total_earned_base = 0.0
        earned_this_week_base = 0.0
        earned_today_base = 0.0

        # 3. Income parsing using Polars
        if income_data:
            df = pl.DataFrame(income_data)
            df = self._normalize_to_base(df, "input_amount", exchange_rate)

            if df.schema["date"] == pl.String:
                df = df.with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

            total_earned_base = df[f"input_amount_{self.base_currency.lower()}"].sum()
            earned_this_week_base = df.filter(pl.col("date") >= start_of_week)[f"input_amount_{self.base_currency.lower()}"].sum()
            earned_today_base = df.filter(pl.col("date") == current_date)[f"input_amount_{self.base_currency.lower()}"].sum()

        earned_before_week = max(0.0, total_earned_base - earned_this_week_base)

        # 4. Weekly Hustle Math
        days_left_from_monday = (end_of_month - start_of_week).days
        weeks_left_from_monday = max(1.0, days_left_from_monday / 7.0)

        total_burn_plus_deficit = gross_monthly_burn_base + safety_net_deficit

        gross_weekly_target = (total_burn_plus_deficit - earned_before_week) / weeks_left_from_monday
        remaining_weekly_target = max(0.0, gross_weekly_target - earned_this_week_base)

        # 5. Daily Grind Math
        remaining_days_in_month = (end_of_month - current_date).days
        remaining_to_earn_total = max(0.0, gross_monthly_burn_base - total_earned_base)

        if remaining_days_in_month > 0:
            daily_goal = (remaining_to_earn_total + safety_net_deficit) / remaining_days_in_month
        else:
            daily_goal = remaining_to_earn_total + safety_net_deficit

        return {
            "safe_to_spend": float(safe_to_spend),
            "remaining_monthly_burn_base": float(remaining_monthly_burn_base),
            "total_spent_this_month_base": float(total_spent_this_month_base),
            f"monthly_target_{self.base_currency.lower()}": float(gross_monthly_burn_base),
            f"remaining_to_earn_{self.base_currency.lower()}": float(remaining_to_earn_total + safety_net_deficit),
            f"daily_hustle_{self.base_currency.lower()}": float(daily_goal),
            f"gross_weekly_target_{self.base_currency.lower()}": float(gross_weekly_target),
            f"remaining_weekly_target_{self.base_currency.lower()}": float(remaining_weekly_target),
            f"total_earned_{self.base_currency.lower()}": float(total_earned_base),
            f"earned_today_{self.base_currency.lower()}": float(earned_today_base or 0.0),
        }

    def get_dashboard_metrics(
        self,
        liquid_base: float,
        gross_monthly_burn_base: float,
        total_spent_this_month_base: float,
        safety_net_months: int,
        pacing_enabled: bool,
        income_data: List[Dict],
        exchange_rate: float,
        current_date: datetime.date = None,
    ) -> Dict[str, float]:
        """Retrieves a comprehensive set of dashboard metrics by calculating dynamic goals.

        This method acts as an orchestrator, calling `calculate_dynamic_goals`
        to generate the necessary financial insights for the user dashboard.

        Args:
            liquid_base: The current amount of liquid cash available in the base currency.
            gross_monthly_burn_base: The total estimated monthly expenses in the base currency.
            total_spent_this_month_base: The total amount already spent this month in the base currency.
            safety_net_months: The desired number of months of gross burn
                to keep as a safety net.
            pacing_enabled: A boolean indicating whether daily/weekly pacing
                should be applied to goals.
            income_data: A list of dictionaries, where each dictionary represents
                an income entry.
            exchange_rate: The exchange rate to convert from the local currency
                to the base currency.
            current_date: An optional datetime.date object representing the current date.
                Defaults to today's date if not provided.

        Returns:
            A dictionary containing various calculated financial metrics, as returned
            by `calculate_dynamic_goals`.
        """
        if current_date is None:
            current_date = datetime.date.today()

        dynamic_goals = self.calculate_dynamic_goals(
            gross_monthly_burn_base=gross_monthly_burn_base,
            total_spent_this_month_base=total_spent_this_month_base,
            income_data=income_data,
            exchange_rate=exchange_rate,
            liquid_base=liquid_base,
            target_safety_net_months=float(safety_net_months),
            pacing_enabled=pacing_enabled,
            current_date=current_date,
        )

        # We are now just a passthrough for the most part
        return dynamic_goals

    def get_income_sources(self, income_data: List[Dict], exchange_rate: float) -> Dict[str, float]:
        """Aggregates income data by source and returns total earned per source in base currency.

        This method processes a list of income dictionaries, normalizes the
        amounts to the base currency, and then groups them by their source
        to provide a summary of income earned from each source.

        Args:
            income_data: A list of dictionaries, where each dictionary represents
                an income entry and contains keys like 'source', 'input_amount', and 'currency'.
            exchange_rate: The exchange rate to convert from the local currency
                to the base currency.

        Returns:
            A dictionary where keys are income sources (str) and values are the
            total earned from that source in the base currency (float).
            Returns an empty dictionary if no income data is provided.
        """
        if not income_data:
            return {}

        df = pl.DataFrame(income_data)
        df = self._normalize_to_base(df, "input_amount", exchange_rate)

        # Group by 'source' and sum the base currency amounts
        grouped = df.group_by("source").agg(pl.col(f"input_amount_{self.base_currency.lower()}").sum())

        sources = grouped["source"].to_list()
        amounts = grouped[f"input_amount_{self.base_currency.lower()}"].to_list()

        return dict(zip(sources, amounts))
