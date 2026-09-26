"""
Schwab rebalance bot.

Run on whatever schedule you like (via Task Scheduler / cron). Each run:

    1. Pulls current cash + position values for the account.
    2. Pulls a live quote for each ticker in config.TARGETS.
    3. Computes each ticker's % of TOTAL account value (cash + all three
       positions) and compares it to its target % from config.py.
    4. Greedily plans buys one share at a time: buys 1 share of whichever
       ticker is currently most underweight, recalculates, and repeats.
       This naturally spreads the available cash across multiple
       underweight tickers in a single run, prioritizing whichever is
       furthest below target at each step.
    5. Places one market order per ticker in the resulting plan.

This bot never sells. If no ticker is underweight, or there isn't enough
cash to buy even one share of the cheapest underweight ticker, it logs
that and exits without placing an order.

Everything is logged to rebalance_log.txt.

IMPORTANT: This places real trades against your live Schwab account unless
DRY_RUN = True in config.py. Test thoroughly in dry-run mode first.
"""

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from support import account as AccountSupport
from support import market_data as MarketData

from bots.balance import config
from config import master as master_config

try:
    from schwab.auth import easy_client
    from schwab.orders.equities import equity_buy_market
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)


# --- logging -----------------------------------------------------------------

logging.basicConfig(
    filename=config.LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)
log = logging.getLogger("rebalance_bot")



#### rebalance decision #########################################################
#
# Greedily allocates available cash across underweight tickers, one whole
# share at a time: at each step, buy 1 share of whichever ticker
# currently has the largest gap below its target %, then recompute gaps
# and repeat. Stops when no ticker is underweight anymore, or when
# remaining cash can't cover even the cheapest still-underweight ticker.
#
# Buying doesn't change total account value (cash converts directly into
# position value), so total_value is computed once and held constant
# throughout the loop.
#
# Returns a dict of {ticker: shares_to_buy}, only including tickers with
# shares_to_buy > 0.
#################################################################################
def plan_buys(cash, position_values, prices):
    values = dict(position_values)
    remaining_cash = cash
    total_value = cash + sum(values.values())
    shares_to_buy = {ticker: 0 for ticker in config.TARGETS}

    if total_value <= 0:
        log.warning("Total account value is $0 or negative; nothing to do.")
        return {}

    log.info("Total account value: $%.2f (cash: $%.2f)", total_value, cash)

    while True:
        gaps = {}
        for ticker, target_pct in config.TARGETS.items():
            current_pct = values[ticker] / total_value
            gaps[ticker] = target_pct - current_pct  # positive == underweight

        # Only consider tickers that are underweight AND affordable right now.
        candidates = {
            ticker: gap for ticker, gap in gaps.items()
            if gap > 0 and prices[ticker] <= remaining_cash
        }
        if not candidates:
            break

        best_ticker = max(candidates, key=candidates.get)
        price = prices[best_ticker]

        shares_to_buy[best_ticker] += 1
        remaining_cash -= price
        values[best_ticker] += price

    log.info("Remaining cash after planned buys: $%.2f", remaining_cash)
    for ticker, target_pct in config.TARGETS.items():
        final_pct = values[ticker] / total_value
        log.info(
            "  %s: target=%.2f%% final=%.2f%% shares_to_buy=%s",
            ticker, target_pct * 100, final_pct * 100, shares_to_buy[ticker],
        )

    return {ticker: n for ticker, n in shares_to_buy.items() if n > 0}

###################
# Returns client
###################
def get_client():
    if not master_config.API_KEY or not master_config.APP_SECRET:
        log.error("SCHWAB_API_KEY / SCHWAB_APP_SECRET are not set as environment variables.")
        sys.exit(1)
    client = easy_client(
        api_key=master_config.API_KEY,
        app_secret=master_config.APP_SECRET,
        callback_url=master_config.CALLBACK_URL,
        token_path=master_config.TOKEN_PATH,
    )
    return client


#################################################
# Returns account hash if it is defined in the 
# config file otherwise it will fetch the first
# hash attached to the account
#################################################
def get_account_hash(client):
    if config.ACCOUNT_HASH:
        return config.ACCOUNT_HASH

    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()
    if not accounts:
        raise RuntimeError("No linked Schwab accounts found for this token.")
    if len(accounts) > 1:
        log.warning(
            "Multiple linked accounts found and ACCOUNT_HASH is not set in "
            "master_config.py -- defaulting to the first one (%s). Run "
            "list_accounts.py to see all of them and set ACCOUNT_HASH "
            "explicitly to avoid relying on this default.",
            accounts[0]["accountNumber"],
        )
    return accounts[0]["hashValue"]

# --- order placement -----------------------------------------------------------

def place_buy(client, account_hash, symbol, quantity, price):
    actual_cost = quantity * price
    log.info(
        "REBALANCE BUY TRIGGER: %s shares of %s @ ~$%.2f (~$%.2f total)",
        quantity, symbol, price, actual_cost,
    )

    if config.DRY_RUN:
        log.info("[DRY RUN] Would place market order for %s shares of %s", quantity, symbol)
    else:
        order = equity_buy_market(symbol, quantity).build()
        resp = client.place_order(account_hash, order)
        resp.raise_for_status()
        log.info("Order placed successfully. Status: %s", resp.status_code)

    return True


# --- main -----------------------------------------------------------

def main():
    today_str = datetime.now(ZoneInfo(master_config.LOCAL_TIMEZONE)).strftime("%m/%d/%Y")

    log.info("=== Run start %s (DRY_RUN=%s) ===", today_str, config.DRY_RUN)

    client = get_client()
    account_hash = get_account_hash(client)

    cash, position_values = AccountSupport.get_account_snapshot(client, account_hash, config.TARGETS)
    prices = MarketData.get_current_prices(client, list(config.TARGETS.keys()))

    buy_plan = plan_buys(cash, position_values, prices)

    if not buy_plan:
        log.info("No underweight ticker is affordable right now. No orders placed this run.")
        log.info("=== Run complete ===\n")
        return

    for ticker, shares in buy_plan.items():
        place_buy(client, account_hash, ticker, shares, prices[ticker])

    log.info("=== Run complete ===\n")


if __name__ == "__main__":
    main()
