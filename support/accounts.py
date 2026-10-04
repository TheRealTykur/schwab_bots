"""
Shared Schwab account/client helpers.
"""

import sys

from config import master as master_config

try:
    from schwab.auth import easy_client
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)

from support import market_data


def get_client():
    """Create and return the shared Schwab API client."""
    if not master_config.API_KEY or not master_config.APP_SECRET:
        raise RuntimeError(
            "SCHWAB_API_KEY / SCHWAB_APP_SECRET are not set as environment variables."
        )

    return easy_client(
        api_key=master_config.API_KEY,
        app_secret=master_config.APP_SECRET,
        callback_url=master_config.CALLBACK_URL,
        token_path=master_config.TOKEN_PATH,
    )


def get_hash(client, account_hash=None, log=None):
    """
    Return the configured account hash or, if none is configured, the first
    hash returned by Schwab.

    If multiple linked accounts exist and no hash was configured, a warning is
    emitted through the caller's logger when one is supplied.
    """
    if account_hash:
        return account_hash

    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()

    if not accounts:
        raise RuntimeError("No linked Schwab accounts found for this token.")

    if len(accounts) > 1 and log is not None:
        log.warning(
            "Multiple linked accounts found and ACCOUNT_HASH is not set. "
            "Defaulting to the first one (%s). Set ACCOUNT_HASH explicitly "
            "to avoid relying on this default.",
            accounts[0].get("accountNumber", "?"),
        )

    return accounts[0]["hashValue"]


########################################################
# Returns float for cash balance for the given account.
########################################################
def get_cash_balance(client, account_hash):
    resp = client.get_account(account_hash)
    resp.raise_for_status()
    data = resp.json()
    balances = data.get("securitiesAccount", {}).get("currentBalances", {})
    return float(balances.get("cashBalance", 0))


#######################################################################
# Shares currently held of one specific symbol. Returns 0 if not held.
#######################################################################
def get_position_quantity(client, account_hash, symbol):
    for pos in market_data.get_positions(client, account_hash):
        if pos["symbol"] == symbol:
            return pos["quantity"]
    return 0


#########################################################################
# Total account equity (cash + all positions).
#########################################################################
def get_portfolio_value(client, account_hash):
    resp = client.get_account(account_hash)
    resp.raise_for_status()
    data = resp.json()
    balances = data.get("securitiesAccount", {}).get("currentBalances", {})
    return float(balances.get("liquidationValue", 0))


######################################################################
# Returns (cash, position_values) where position_values is a dict of
# {ticker: market_value} for a provided list of tickers.
######################################################################
def get_account_snapshot(client, account_hash, ticker_list):
    resp = client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
    resp.raise_for_status()
    data = resp.json()

    securities_account = data["securitiesAccount"]
    balances = securities_account["currentBalances"]
    cash = float(balances.get("cashBalance", balances.get("cashAvailableForTrading", 0)))

    position_values = {ticker: 0.0 for ticker in ticker_list}
    for pos in securities_account.get("positions", []):
        symbol = pos["instrument"]["symbol"]
        if symbol in position_values:
            position_values[symbol] = float(pos.get("marketValue", 0))

    return cash, position_values
