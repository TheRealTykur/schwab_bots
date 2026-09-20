"""
Schwab daily DCA bot.

Run once a day (via Task Scheduler / cron). Each run places one market buy
for a fixed number of whole shares (DAILY_SHARE_QUANTITY in config.py) --
no dollar-amount math, no price-based sizing. It assumes it's only invoked
once per day (i.e. your cron job / scheduled task isn't set to fire more
than once) -- there's no internal guard against running it twice in a day.

Everything is logged to bot_log.txt.

IMPORTANT: This places real trades against your live Schwab account unless
DRY_RUN = True in config.py. Test thoroughly in dry-run mode first.
"""

import logging
import sys

# --- logging -----------------------------------------------------------------
logging.basicConfig(
    filename=config.LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)
log = logging.getLogger("dca_bot")

from datetime import datetime
from zoneinfo import ZoneInfo
import time

from dca_bot import config
from config import master as master_config

from support import account as AccountSupport
from support import market_data as MarketData

try:
    from schwab.auth import easy_client
    from schwab.orders.equities import equity_buy_market
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)

MAX_ORDER_RETRIES = 3
RETRY_DELAY_SECONDS = 5

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
    if master_config.ACCOUNT_HASH:
        return master_config.ACCOUNT_HASH

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
        "DAILY BUY TRIGGER: %s shares of %s @ ~$%.2f (~$%.2f total)",
        quantity, symbol, price, actual_cost,
    )

    if config.DRY_RUN:
        log.info("[DRY RUN] Would place market order for %s shares of %s", quantity, symbol)
    else:
        order = equity_buy_market(symbol, quantity).build()
        for attempt in range(1, MAX_ORDER_RETRIES + 1):
            try:
                resp = client.place_order(account_hash, order)
                resp.raise_for_status()
                log.info("Order placed successfully. Status: %s", resp.status_code)
                break
            except Exception as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                is_server_error = status_code is not None and status_code >= 500

                if is_server_error and attempt < MAX_ORDER_RETRIES:
                    log.warning("place_order failed with a server error (attempt %d/%d): %s."
                                "Retrying in %d seconds...",
                                attempt, MAX_ORDER_RETRIES, e, RETRY_DELAY_SECONDS,
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue
                else:
                    log.error(
                             "place_order failed and will not be retried (attempt %d/%d): %s",
                             attempt, MAX_ORDER_RETRIES, e,
                    )
                    raise
    return True


# --- main -----------------------------------------------------------
def main():
    today_str = datetime.now(ZoneInfo(master_config.LOCAL_TIMEZONE)).strftime("%m/%d/%Y")

    log.info("=== Run start %s (DRY_RUN=%s) ===", today_str, config.DRY_RUN)

    client = get_client()
    account_hash = get_account_hash(client)
    price = MarketData.get_current_price(client, config.SYMBOL)
    log.info("%s current price: $%.2f", config.SYMBOL, price)

    required_cash = price* config.DAILY_SHARE_QUANTITY * config.CASH_BUFFER_MULTIPLIER
    cash_balance = AccountSupport.get_cash_balance(client, account_hash)

    log.info(
        "Cash Balance: $%.2f. Required (%.1fx buffer for %d shares @ $%.2f): $%.2f",
        cash_balance, config.CASH_BUFFER_MULTIPLIER, config.DAILY_SHARE_QUANTITY, price, required_cash,
    )

    if cash_balance < required_cash:
        log.warning(
            "Skipping buy: cash balance ($%.2f) is below the required buffer "
            "($%.2f). No order placed today.",
            cash_balance, required_cash,
        )
        log.info("=== Run complete (skipped, insufficient cash) ===\n")
        return

    place_buy(
        client, account_hash, config.SYMBOL, config.DAILY_SHARE_QUANTITY,
        price,
    )

    log.info("=== Run complete ===\n")


if __name__ == "__main__":
    main()
