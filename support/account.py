"""
account.py

TODO: ADD ABSTRACT
"""
from support import market_data


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
#Shares currently held of one specific symbol. Returns 0 if not held.
#######################################################################
def get_position_quantity(client, account_hash, symbol):
    for pos in market_data.get_positions(client, account_hash):
        if pos["symbol"] == symbol:
            return pos["quantity"]
    return 0


#########################################################################
# Total account equity (cash + all positions).
#
# UNVERIFIED field name -- uses currentBalances.liquidationValue, which
# is the commonly documented field for total account value across
# Schwab API wrappers, but hasn't been confirmed against this project's
# own account data. Cross-check against the actual value shown in the
# Schwab app the first time you use this.
#########################################################################
def get_portfolio_value(client, account_hash):
    resp = client.get_account(account_hash)
    resp.raise_for_status()
    data = resp.json()
    balances = data.get("securitiesAccount", {}).get("currentBalances", {})
    return float(balances.get("liquidationValue", 0))


######################################################################
# Returns (cash, position_values) where position_values is a dict of
# {ticker: market_value} for a provided list of tickers
# (tickers with no position at all are treated as $0).
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