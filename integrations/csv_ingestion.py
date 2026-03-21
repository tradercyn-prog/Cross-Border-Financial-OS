import csv
import logging
from typing import Dict, List


class SchwabParser:
    """Bulletproof parser for Charles Schwab 'Positions' CSV files.

    This class provides robust parsing capabilities for CSV files exported
    from Charles Schwab, specifically designed to extract asset position data.
    It handles variations in CSV formatting, including invisible BOM characters,
    and flexible header matching to ensure reliable data extraction.
    """

    def parse(self, file_path: str) -> List[Dict]:
        """Parses a Charles Schwab 'Positions' CSV file to extract asset data.

        The method reads the CSV file, identifies the header row, and then
        extracts relevant asset information such such as asset name, balance,
        currency, asset type, and liquidity status. It includes logic to
        clean and standardize data, such as handling cash accounts and
        filtering out irrelevant or zero-balance entries.

        Args:
            file_path: The full path to the Charles Schwab 'Positions' CSV file.

        Returns:
            A list of dictionaries, where each dictionary represents a parsed
            asset with keys like 'asset_name', 'balance', 'currency',
            'asset_type', and 'is_liquid'. Returns an empty list if parsing
            fails or no valid data is found.
        """
        parsed_assets: List[Dict] = []

        try:
            # utf-8-sig automatically strips the invisible BOM character
            with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                lines = f.readlines()

            header_idx = -1

            # 1. Locate the header row
            for i, line in enumerate(lines[:30]):
                line_lower = line.lower()
                if "symbol" in line_lower and ("value" in line_lower or "quantity" in line_lower or "price" in line_lower):
                    header_idx = i
                    break

            if header_idx == -1:
                logging.error("Could not find valid Schwab header row.")
                return []

            # 2. Tokenize and Index
            reader = csv.reader(lines[header_idx:])
            raw_headers = next(reader)

            # Clean headers: strip whitespace, quotes, and make lowercase
            headers = [str(h).strip().replace('"', "").lower() for h in raw_headers]

            symbol_idx = -1
            value_idx = -1

            # THE FIX: Stop using exact == matches. Schwab loves to add parentheses.
            for i, h in enumerate(headers):
                if "symbol" in h:
                    symbol_idx = i
                elif "value" in h or "mkt val" in h:
                    value_idx = i

            if symbol_idx == -1 or value_idx == -1:
                logging.error(f"Found header row but missing target columns. Headers found: {headers}")
                return []

            # 3. Extract the Data
            for row in reader:
                # Skip broken rows
                if not row or len(row) <= max(symbol_idx, value_idx):
                    continue

                symbol = str(row[symbol_idx]).strip()
                market_value_str = str(row[value_idx]).strip()

                # Skip empty rows or footer totals
                if not symbol or "total" in symbol.lower() or not market_value_str:
                    continue

                # Standardize cash (Your CSV has "Cash & Cash Investments")
                if "cash" in symbol.lower() or symbol.lower() == "sweep":
                    symbol = "Schwab Cash"

                # Scrub the financial formatting
                clean_value = market_value_str.replace("$", "").replace(",", "")

                try:
                    balance = float(clean_value)

                    # Ignore zeroed-out positions (Like your "Futures Cash" row)
                    if balance <= 0:
                        continue

                    parsed_assets.append(
                        {
                            "asset_name": symbol,
                            "balance": balance,
                            "currency": "USD",
                            "asset_type": "Brokerage",
                            "is_liquid": False,  # Cross-border transfers take days. This is illiquid.
                        }
                    )
                except ValueError:
                    # Junk row data, skip it
                    continue

        except Exception as e:
            logging.error(f"Critical error parsing Schwab CSV: {e}")

        return parsed_assets
