"""
schwab_utils.py

A library of reusable Schwab account/market-data helper functions -- cash
balance, moving averages, percent from high, and percent change over a
period. Import these into other scripts (schwab_bot.py, buy_stock.py,
etc.) rather than duplicating this logic in each one.

These functions take an already-authenticated `client` (and `account_hash`
where needed) as arguments 

All price-history-based functions (get_moving_average, get_percent_from_high,
get_percent_change) use TRADING days, not calendar days -- e.g. a "20-day
moving average" means the last 20 days the market was actually open, not
the last 20 calendar days. Under the hood they pull extra calendar days as
a buffer for weekends/holidays, then trim to the exact trading-day count
requested.

For a quick manual sanity-check of these functions against a real account,
see schwab_utils_test.py.
"""
import os 
import sys
import logging

sys.path.append(os.path.abspath(".."))

from datetime import datetime, timedelta, timezone
import config

try:
    from schwab.auth import easy_client
    from schwab.orders.equities import equity_buy_market
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)


log = logging.getLogger(__name__)

# Standard trading-day approximations for each period -- not exact
# calendar dates (e.g. "a month ago" is approximated as 21 trading days
# back, not literally 30 calendar days back).
PERIOD_TRADING_DAYS = {
    "week": 5,
    "month": 21,
    "year": 252,
}

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
        # lastPrice is the most recent trade price
        prices[symbol] = float(quote["lastPrice"])
    return prices

########################################################
# Returns float for cash balance for the given account.
########################################################
def get_cash_balance(client, account_hash):
    resp = client.get_account(account_hash)
    resp.raise_for_status()
    data = resp.json()
    balances = data.get("securitiesAccount", {}).get("currentBalances", {})
    return float(balances.get("cashBalance", 0))


###########################################################################
# Internal helper: fetches daily closing prices for `symbol`, returning
# the most recent `trading_days` closes in chronological order (oldest
# first). Pulls extra calendar days as a buffer for weekends/holidays.
###########################################################################
def _get_daily_closes(client, symbol, trading_days):
    now = datetime.now(timezone.utc)
    # ~1.6x calendar-day buffer comfortably covers weekends; padded
    # further for holidays.
    calendar_days_back = int(trading_days * 1.6) + 10

    resp = client.get_price_history_every_day(
        symbol,
        start_datetime=now - timedelta(days=calendar_days_back),
        end_datetime=now,
    )
    resp.raise_for_status()
    candles = resp.json().get("candles", [])

    if len(candles) < trading_days:
        raise ValueError(
            f"Only found {len(candles)} trading days of history for "
            f"{symbol}, need {trading_days}. The symbol may be too newly "
            f"listed, or the lookback window needs to be wider."
        )

    closes = [c["close"] for c in candles]
    return closes[-trading_days:]


###########################################################################
# Simple moving average of `symbol`'s closing price over the last
# `trading_days` trading days. e.g. get_moving_average(client, "VOO", 50)
# for the 50-day moving average.
###########################################################################
def get_moving_average(client, symbol, trading_days):
    closes = _get_daily_closes(client, symbol, trading_days)
    return sum(closes) / len(closes)


#######################################################################
# How far the current price is from the highest close in the lookback
# window, as a percent. Negative means currently below that high (the
# normal case); 0 means at the high right now.
#
# Default lookback is 252 trading days (~1 year, the standard "52-week
# high" convention). Pass a smaller number for a shorter-term high, e.g.
# 20 for a 20-day high.
#######################################################################
def get_percent_from_high(client, symbol, lookback_trading_days=252):
    closes = _get_daily_closes(client, symbol, lookback_trading_days)
    period_high = max(closes)
    current_price = get_current_price(client, symbol)
    return (current_price - period_high) / period_high * 100


########################################################################
# Percent change in `symbol`'s price over the given period, comparing
# the current live price to the close from `period` ago.
#
# `period` must be one of: "week", "month", "year".
########################################################################
def get_percent_change(client, symbol, period):

    trading_days = PERIOD_TRADING_DAYS.get(period)
    if trading_days is None:
        raise ValueError(
            f"period must be one of {list(PERIOD_TRADING_DAYS)}, got {period!r}"
        )

    closes = _get_daily_closes(client, symbol, trading_days + 1)
    price_then = closes[0]
    current_price = get_current_price(client, symbol)
    return (current_price - price_then) / price_then * 100


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
        # Net quantity: longQuantity for a normal long position, minus
        # shortQuantity if short. Most accounts will just have longQuantity.
        quantity = pos.get("longQuantity", 0) - pos.get("shortQuantity", 0)
        positions.append({
            "symbol": instrument.get("symbol"),
            "quantity": quantity,
            "market_value": pos.get("marketValue"),
        })
    return positions


#######################################################################
#Shares currently held of one specific symbol. Returns 0 if not held.
#######################################################################
def get_position_quantity(client, account_hash, symbol):
    for pos in get_positions(client, account_hash):
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


###########################################################################
# Percent change since today's open/previous close, using the quote's
# own lastPrice vs closePrice (previous session's close).
#
# UNVERIFIED field name -- "closePrice" is the commonly documented name
# for previous close in Schwab's quote schema; if this raises a KeyError,
# print the raw quote response to find the actual field name.
###########################################################################
def get_day_change(client, symbol):
    resp = client.get_quote(symbol)
    resp.raise_for_status()
    quote = resp.json()[symbol]["quote"]
    last_price = float(quote["lastPrice"])
    prev_close = float(quote["closePrice"])
    return (last_price - prev_close) / prev_close * 100


###########################################################################
# Relative Strength Index over `period` trading days (14 is the standard
# default). Ranges 0-100; conventionally >70 = overbought, <30 = oversold.
# Computed locally from closing prices -- no separate Schwab endpoint
# for this.
###########################################################################
def get_rsi(client, symbol, period=14):
    closes = _get_daily_closes(client, symbol, period + 1)
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


######################################################################
# Checks whether the short-window MA is currently above or below the
# long-window MA -- the classic "golden cross" (short above long,
# bullish signal) / "death cross" (short below long, bearish signal).
#
# Returns "golden_cross", "death_cross", or "no_crossover_data" (the
# latter only if something upstream returns equal values, effectively
# never in practice).
######################################################################
def detect_ma_crossover(client, symbol, short_window=50, long_window=200):
    short_ma = get_moving_average(client, symbol, short_window)
    long_ma = get_moving_average(client, symbol, long_window)

    if short_ma > long_ma:
        return "golden_cross"
    elif short_ma < long_ma:
        return "death_cross"
    return "no_crossover_data"


###################
# Returns client
###################
def get_client(log):
    if not config.Master_Config.API_KEY or not config.Master_Config.APP_SECRET:
        log.error("SCHWAB_API_KEY / SCHWAB_APP_SECRET are not set as environment variables.")
        sys.exit(1)
    client = easy_client(
        api_key=config.Master_Config.API_KEY,
        app_secret=config.Master_Config.APP_SECRET,
        callback_url=config.Master_Config.CALLBACK_URL,
        token_path=config.Master_Config.TOKEN_PATH,
    )
    return client


#################################################
# Returns account hash if it is defined in the 
# config file otherwise it will fetch the first
# hash attached to the account
#################################################
def get_account_hash(client, log):
    if config.Master_Config.ACCOUNT_HASH:
        return config.Master_Config.ACCOUNT_HASH

    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()
    if not accounts:
        raise RuntimeError("No linked Schwab accounts found for this token.")
    if len(accounts) > 1:
        log.warning(
            "Multiple linked accounts found and ACCOUNT_HASH is not set in "
            "config.Master_Config.py -- defaulting to the first one (%s). Run "
            "list_accounts.py to see all of them and set ACCOUNT_HASH "
            "explicitly to avoid relying on this default.",
            accounts[0]["accountNumber"],
        )
    return accounts[0]["hashValue"]


######################################################################
# Returns (cash, position_values) where position_values is a dict of
# {ticker: market_value} for whichever of config.TARGETS are currently
# held (tickers with no position at all are treated as $0).
######################################################################
def get_account_snapshot(client, account_hash):
    resp = client.get_account(account_hash, fields=[client.Account.Fields.POSITIONS])
    resp.raise_for_status()
    data = resp.json()

    securities_account = data["securitiesAccount"]
    balances = securities_account["currentBalances"]
    cash = float(balances.get("cashBalance", balances.get("cashAvailableForTrading", 0)))

    position_values = {ticker: 0.0 for ticker in config.TARGETS}
    for pos in securities_account.get("positions", []):
        symbol = pos["instrument"]["symbol"]
        if symbol in position_values:
            position_values[symbol] = float(pos.get("marketValue", 0))

    return cash, position_values