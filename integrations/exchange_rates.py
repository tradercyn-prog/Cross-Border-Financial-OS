import logging
from typing import List, Optional

from core.state import global_state
from integrations.wise_api import WiseClient


class ExchangeRateProvider:
    """Provides a unified interface for fetching exchange rates from different sources.

    Currently, this provider is configured to use the Wise.com API for fetching
    live exchange rates and account balances. It abstracts the underlying API
    calls, allowing for potential future integration of multiple exchange rate
    providers.
    """

    def __init__(self) -> None:
        """Initializes the ExchangeRateProvider.

        A WiseClient instance is created to handle interactions with the Wise.com API.
        In future iterations, this could be extended to manage multiple API clients
        for various exchange rate sources.
        """
        self.wise_client = WiseClient()
        # In the future, we could have a list of clients and try them in order.
        # self.clients = [WiseClient(), OtherClient()]

    def get_live_rate(self, source_currency: Optional[str] = None, target_currency: Optional[str] = None) -> Optional[float]:
        """Fetches the live exchange rate from the primary provider (Wise.com).

        If `source_currency` or `target_currency` are not provided, they default
        to the `base_currency` and `local_currency` respectively, as defined
        in the global application state.

        Args:
            source_currency: The three-letter currency code of the source currency
                (e.g., 'USD'). Defaults to `global_state.base_currency`.
            target_currency: The three-letter currency code of the target currency
                (e.g., 'PHP'). Defaults to `global_state.local_currency`.

        Returns:
            The exchange rate as a float, or None if the rate cannot be fetched
            from the configured provider.
        """
        source_currency = source_currency or global_state.base_currency
        target_currency = target_currency or global_state.local_currency
        logging.info(f"Fetching live rate for {source_currency}->{target_currency}")

        # Currently, we only have one provider
        rate = self.wise_client.get_exchange_rate(source_currency, target_currency)

        if rate is None:
            logging.warning(
                f"Could not fetch live rate for {source_currency}->{target_currency} "
                f"from Wise.com. Consider implementing a fallback mechanism."
            )
            # Fallback strategy could be to return a stale rate from a database,
            # or a hardcoded default, depending on requirements.

        return rate

    def get_live_balances(self) -> List[dict]:
        """Fetches live account balances from the primary provider (Wise.com).

        This method retrieves a list of account balances directly from the
        Wise.com API.

        Returns:
            A list of dictionaries, where each dictionary represents an account
            balance. Returns an empty list if balances cannot be fetched.
        """
        logging.info("Fetching live balances from Wise")

        balances = self.wise_client.get_live_balances()

        if not balances:
            logging.warning("Could not fetch live balances from Wise.com.")

        return balances


# Global instance for easy access
exchange_rate_provider = ExchangeRateProvider()
