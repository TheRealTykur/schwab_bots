"""
schwab_utils_test.py

Quick manual sanity-check of every function in schwab_utils.py, run
against a real Schwab account. Not an automated test suite (no
assertions) -- it's meant for eyeballing that each function returns a
sane-looking value, especially the ones flagged UNVERIFIED in
schwab_utils.py's docstrings (get_portfolio_value, get_day_change,
get_positions, is_market_open).

Usage:
    python3 schwab_utils_test.py SYMBOL
"""

import os 
import sys

sys.path.append(os.path.abspath(".."))

import config
import schwab_utils as su

try:
    from schwab.auth import easy_client
except ImportError:
    print("schwab-py is not installed, or config.py isn't in this directory.")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 schwab_utils_test.py SYMBOL")
        sys.exit(1)

    symbol = sys.argv[1].upper()

    client = easy_client(
        api_key=config.API_KEY,
        app_secret=config.APP_SECRET,
        callback_url=config.CALLBACK_URL,
        token_path=config.TOKEN_PATH,
    )

    account_hash = config.ACCOUNT_HASH
    if not account_hash:
        resp = client.get_account_numbers()
        resp.raise_for_status()
        accounts = resp.json()
        account_hash = accounts[0]["hashValue"] if accounts else None

    print(f"Market open right now: {su.is_market_open(client)}")
    print(f"Current price:       ${su.get_current_price(client, symbol):.2f}")
    print(f"Day change:           {su.get_day_change(client, symbol):.2f}%")
    if account_hash:
        print(f"Cash balance:        ${su.get_cash_balance(client, account_hash):.2f}")
        print(f"Portfolio value:     ${su.get_portfolio_value(client, account_hash):.2f}")
        print(f"Position in {symbol}:    {su.get_position_quantity(client, account_hash, symbol)} shares")
        print("All positions:")
        for pos in su.get_positions(client, account_hash):
            print(f"  {pos['symbol']}: {pos['quantity']} shares, ${pos['market_value']}")
    print(f"20-day MA:           ${su.get_moving_average(client, symbol, 20):.2f}")
    print(f"50-day MA:           ${su.get_moving_average(client, symbol, 50):.2f}")
    print(f"200-day MA:          ${su.get_moving_average(client, symbol, 200):.2f}")
    print(f"MA crossover:         {su.detect_ma_crossover(client, symbol)}")
    print(f"14-day RSI:           {su.get_rsi(client, symbol):.2f}")
    print(f"% from 52-wk high:    {su.get_percent_from_high(client, symbol):.2f}%")
    print(f"% change (week):      {su.get_percent_change(client, symbol, 'week'):.2f}%")
    print(f"% change (month):     {su.get_percent_change(client, symbol, 'month'):.2f}%")
    print(f"% change (year):      {su.get_percent_change(client, symbol, 'year'):.2f}%")


if __name__ == "__main__":
    main()
