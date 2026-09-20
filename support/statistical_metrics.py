"""
statistical_metrics.py

TODO: ADD ABSTRACT
"""

from datetime import datetime, timedelta, timezone
from support import market_data

# Standard trading-day approximations for each period -- not exact
# calendar dates (e.g. "a month ago" is approximated as 21 trading days
# back, not literally 30 calendar days back).
PERIOD_TRADING_DAYS = {
    "week": 5,
    "month": 21,
    "year": 252,
}

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
    current_price = market_data.get_current_price(client, symbol)
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
    current_price = market_data.get_current_price(client, symbol)
    return (current_price - price_then) / price_then * 100


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
