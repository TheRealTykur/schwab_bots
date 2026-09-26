"""
Prints current positions (with market value) and cash balance for the
configured Schwab account. Useful for sanity-checking numbers before
wiring them into the rebalance bot.

Usage:
    python check_holdings.py
"""

import sys
import config

try:
    from schwab.auth import easy_client
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)


def get_client():
    if not config.Master_Config.API_KEY or not config.Master_Config.APP_SECRET:
        print("SCHWAB_API_KEY / SCHWAB_APP_SECRET are not set as environment variables.")
        sys.exit(1)
    return easy_client(
        api_key=config.Master_Config.API_KEY,
        app_secret=config.Master_Config.APP_SECRET,
        callback_url=config.Master_Config.CALLBACK_URL,
        token_path=config.Master_Config.TOKEN_PATH,
    )


def get_account_hash(client):
    if config.ACCOUNT_HASH:
        return config.ACCOUNT_HASH
    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()
    if not accounts:
        raise RuntimeError("No linked Schwab accounts found for this token.")
    return accounts[0]["hashValue"]


def main():
    client = get_client()
    account_hash = get_account_hash(client)

    resp = client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
    resp.raise_for_status()
    data = resp.json()

    securities_account = data["securitiesAccount"]
    balances = securities_account["currentBalances"]
    cash = float(balances.get("cashBalance", balances.get("cashAvailableForTrading", 0)))

    positions = securities_account.get("positions", [])

    total_position_value = sum(float(pos.get("marketValue", 0)) for pos in positions)
    total_account_value = cash + total_position_value
    cash_pct = (cash / total_account_value * 100) if total_account_value else 0

    print(f"Cash: ${cash:,.2f} ({cash_pct:.2f}% of total)\n")

    if not positions:
        print("No open positions.")
    else:
        print(f"{'Symbol':<10}{'Quantity':>12}{'Market Value':>16}{'% of Total':>12}")
        for pos in positions:
            symbol = pos["instrument"]["symbol"]
            quantity = float(pos.get("longQuantity", 0))
            market_value = float(pos.get("marketValue", 0))
            pct = (market_value / total_account_value * 100) if total_account_value else 0
            print(f"{symbol:<10}{quantity:>12.4f}{market_value:>16,.2f}{pct:>11.2f}%")

        print(f"\nTotal position value: ${total_position_value:,.2f}")

    print(f"Total account value (cash + positions): ${total_account_value:,.2f}")


if __name__ == "__main__":
    main()
