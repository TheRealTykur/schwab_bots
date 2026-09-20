"""
market_data.py

TODO: ADD ABSTRACT
"""

#########################################################
# Returns float of most recent trade price for `symbol`.
#########################################################
def get_current_price(client, symbol):
    resp = client.get_quote(symbol)
    resp.raise_for_status()
    data = resp.json()
    return float(data[symbol]["quote"]["lastPrice"])


########################################################
# Returns {ticker: last_price} for a list of tickers.
########################################################
def get_current_prices(client, symbols):
    resp = client.get_quotes(symbols)
    resp.raise_for_status()
    data = resp.json()
    prices = {}
    for symbol in symbols:
        quote = data[symbol]["quote"]
        prices[symbol] = float(quote["lastPrice"])
    return prices


############################################################################
# Every held position in the account: list of dicts with symbol,
# quantity, and market_value.
# 
# UNVERIFIED against a live account -- built from schwab-py's documented
# fields=[Account.Fields.POSITIONS] pattern and the field names other
# Schwab API wrappers use (longQuantity, shortQuantity, marketValue).
# Print the raw response once and adjust field names here if anything
# looks off.
############################################################################
def get_positions(client, account_hash):
    resp = client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
    resp.raise_for_status()
    data = resp.json()
    raw_positions = data.get("securitiesAccount", {}).get("positions", [])

    positions = []
    for pos in raw_positions:
        instrument = pos.get("instrument", {})
        quantity = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)
        positions.append({
            "symbol": instrument.get("symbol"),
            "quantity": quantity,
            "market_value": pos.get("marketValue"),
        })
    return positions


###########################################################################
# True if the equity market is open right now, False otherwise.
#
# UNVERIFIED response shape -- built from the general Schwab market-hours
# schema (nested {"equity": {"EQ": {"isOpen": bool, ...}}}), consistent
# across several third-party wrappers, but not confirmed against a live
# call in this project. Useful for skipping a buy cleanly on a holiday
# instead of letting get_quote return stale/errored data.
###########################################################################
def is_market_open(client):
    resp = client.get_market_hours([client.MarketHours.Market.EQUITY])
    resp.raise_for_status()
    data = resp.json()
    equity_hours = data.get("equity", {})

    for product_hours in equity_hours.values():
        return bool(product_hours.get("isOpen", False))
    return False