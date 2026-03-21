import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load the .env file
load_dotenv()


class WiseClient:
    """Client for interacting with the Wise (formerly TransferWise) API.

    This class provides methods to fetch live exchange rates and account balances
    from the Wise API. It includes caching mechanisms for exchange rates to
    reduce API calls and improve performance.
    """

    def __init__(self) -> None:
        """Initializes the WiseClient.

        Retrieves the API token from environment variables, sets up an in-memory
        cache for exchange rates, and defines the cache's time-to-live (TTL).
        """
        self.token: Optional[str] = os.getenv("WISE_API_TOKEN")
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl: int = 3600  # 1 hour in seconds

    def get_exchange_rate(self, source: str = "USD", target: str = "PHP") -> Optional[float]:
        """Fetches the live exchange rate between two currencies from Wise.com.

        The method first checks an in-memory cache for a recent rate. If a valid
        cached rate is found, it is returned. Otherwise, it makes an API call
        to Wise.com. A fallback rate of 56.0 is used if the API token is missing
        or the API call fails.

        Args:
            source: The three-letter currency code of the source currency (e.g., "USD").
            target: The three-letter currency code of the target currency (e.g., "PHP").

        Returns:
            The exchange rate as a float, or None if the rate cannot be fetched
            and no fallback is available (though a fallback is currently implemented).
        """
        pair_key: str = f"{source}_{target}"
        now: float = time.time()

        # 1. Check the local cache first
        if pair_key in self.cache:
            if now - self.cache[pair_key]["timestamp"] < self.cache_ttl:
                logging.info(f"Using cached FX rate for {pair_key}")
                return self.cache[pair_key]["rate"]

        # 2. Guard against missing token
        if not self.token:
            logging.error("No WISE_API_TOKEN found in .env. Using fallback rate.")
            return 56.0

        # 3. Hit the live Wise API
        url: str = f"https://api.wise.com/v1/rates?source={source}&target={target}"
        headers: Dict[str, str] = {"Authorization": f"Bearer {self.token}"}

        try:
            response: requests.Response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data: List[Dict[str, Any]] = response.json()

            if data and len(data) > 0:
                rate: float = float(data[0].get("rate", 56.0))
                # Update cache
                self.cache[pair_key] = {"rate": rate, "timestamp": now}
                logging.info(f"Fetched live FX rate: 1 {source} = {rate} {target}")
                return rate

        except requests.exceptions.RequestException as e:
            logging.error(f"Wise API request failed: {e}. Using fallback rate.")
        except Exception as e:
            logging.error(f"An unexpected error occurred during Wise API request: {e}. Using fallback rate.")

        return 56.0

    def get_live_balances(self) -> List[Dict[str, Any]]:
        """Fetches live account balances for all profiles associated with the API token.

        This method first retrieves all user profiles and then fetches the standard
        balances for each profile using the Wise API. It aggregates and returns
        the parsed balance information. A fallback to an empty list is provided
        if the API token is missing or API calls fail.

        Returns:
            A list of dictionaries, where each dictionary represents an account
            balance with keys like 'id', 'currency', 'balance', and 'profile_type'.
            Returns an empty list if balances cannot be fetched.
        """
        if not self.token:
            logging.error("No WISE_API_TOKEN found in .env. Cannot fetch balances.")
            return []

        headers: Dict[str, str] = {"Authorization": f"Bearer {self.token}"}

        try:
            # 1. Get user profiles
            profiles_url: str = "https://api.wise.com/v2/profiles"
            profiles_response: requests.Response = requests.get(profiles_url, headers=headers, timeout=10)
            profiles_response.raise_for_status()
            profiles: List[Dict[str, Any]] = profiles_response.json()

            if not profiles:
                logging.error("No profiles found for the given API token.")
                return []

            parsed_balances: List[Dict[str, Any]] = []
            for profile in profiles:
                profile_id: int = profile["id"]
                profile_type: str = profile.get("type", "UNKNOWN")
                logging.info(f"Found Wise profile ID: {profile_id} (Type: {profile_type})")

                # 2. Get balances for that profile using v4 endpoint
                balances_url: str = f"https://api.wise.com/v4/profiles/{profile_id}/balances?types=STANDARD"
                balances_response: requests.Response = requests.get(balances_url, headers=headers, timeout=10)
                balances_response.raise_for_status()
                balances_data: List[Dict[str, Any]] = balances_response.json()

                # 3. Parse and append balances for this profile
                for account in balances_data:
                    parsed_balances.append(
                        {
                            "id": str(account.get("id")),
                            "currency": account.get("currency"),
                            "balance": account.get("amount", {}).get("value", 0.0),
                            "profile_type": profile_type,
                        }
                    )

            return parsed_balances

        except requests.exceptions.RequestException as e:
            logging.error(f"Wise API request for balances failed: {e}")
            return []
        except Exception as e:
            logging.error(f"An unexpected error occurred during Wise API request for balances: {e}")
            return []
