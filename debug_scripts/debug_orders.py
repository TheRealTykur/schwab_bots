"""
Diagnostic script: shows exactly which account is being queried and every
order (any status) found for it in the last 60 days. Use this to figure out
why get_last_trade.py isn't finding filled orders -- most likely causes are
either the wrong account being queried, or a date-range edge case.

Run manually:
    python3 debug_orders.py
"""

import sys
from datetime import datetime, timedelta, timezone

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


def main():
    client = get_client()

    print(f"config.ACCOUNT_HASH = {config.ACCOUNT_HASH!r}\n")

    # Show every linked account for reference, so we can compare against
    # whichever one actually gets queried below.
    accounts_resp = client.get_account_numbers()
    accounts_resp.raise_for_status()
    all_accounts = accounts_resp.json()
    print("All linked accounts on this token:")
    for acct in all_accounts:
        print(f"  Account Number: {acct.get('accountNumber')}  Hash: {acct.get('hashValue')}")
    print()

    account_hash = config.ACCOUNT_HASH if config.ACCOUNT_HASH else all_accounts[0]["hashValue"]
    print(f"Querying orders for account hash: {account_hash}\n")

    now = datetime.now(timezone.utc)
    print(f"Query window: {now - timedelta(days=60)} to {now} (UTC)\n")
    resp = client.get_orders_for_account(
        account_hash,
        from_entered_datetime=now - timedelta(days=60),
        to_entered_datetime=now,
        # No status filter this time -- we want to see everything.
    )
    resp.raise_for_status()
    orders = resp.json()

    print(f"Total orders found (any status, last 60 days): {len(orders)}\n")

    if not orders:
        print("Zero orders came back for this account hash. This strongly")
        print("suggests ACCOUNT_HASH in config.py points at the wrong")
        print("account -- try the other hash from the list above.")
        return

    for order in orders:
        leg = order.get("orderLegCollection", [{}])[0]
        symbol = leg.get("instrument", {}).get("symbol", "?")
        print(
            f"  orderId={order.get('orderId')}  status={order.get('status')}  "
            f"symbol={symbol}  entered={order.get('enteredTime')}"
        )


if __name__ == "__main__":
    main()
