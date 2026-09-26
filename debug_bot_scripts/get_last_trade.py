"""
Standalone script: pulls the most recent TRADE transaction on the account
and saves the entire raw transaction JSON to a file. Read-only -- it does
not place, modify, or cancel anything.

Uses get_transactions() rather than get_orders_for_account(). These are
two different Schwab systems: the Orders endpoint reflects the live
order-management system (which can get reset by account changes, e.g.
enabling Thinkorswim), while Transactions is the permanent settlement
ledger and isn't affected by that.

Run manually:
    python3 get_last_trade.py

Uses the same config.py and cached token as schwab_bot.py, but is otherwise
independent -- it's not called by the daily cron job.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import config

try:
    from schwab.auth import easy_client
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)


LAST_TRADE_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "last_trade.json")

# Candidate keys for the transaction's timestamp. "time" is confirmed
# working against a live account; the others are kept as fallbacks in case
# Schwab's schema varies by transaction type.
DATE_FIELD_CANDIDATES = ("time", "tradeDate", "transactionDate", "settlementDate")


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


def _transaction_sort_key(txn):
    for field in DATE_FIELD_CANDIDATES:
        if field in txn:
            return txn[field]
    return ""


def get_last_trade_transaction(client, account_hash):
    """
    Schwab's transactions endpoint caps the lookback at 60 days. Fetches
    every TRADE-type transaction in that window and returns the most
    recent one. Returns None if nothing was found.
    """
    now = datetime.now(timezone.utc)
    resp = client.get_transactions(
        account_hash,
        start_date=now - timedelta(days=60),
        end_date=now,
        transaction_types=client.Transactions.TransactionType.TRADE,
    )
    resp.raise_for_status()
    transactions = resp.json()

    if not transactions:
        return None

    transactions.sort(key=_transaction_sort_key, reverse=True)
    return transactions[0]


def main():
    client = get_client()
    account_hash = get_account_hash(client)

    transaction = get_last_trade_transaction(client, account_hash)
    if transaction is None:
        print("No TRADE transactions found in the last 60 days.")
        return

    with open(LAST_TRADE_OUTPUT_PATH, "w") as f:
        json.dump(transaction, f, indent=2)

    print(f"Saved most recent trade transaction to {LAST_TRADE_OUTPUT_PATH}")
    print(f"  Transaction ID: {transaction.get('transactionId', transaction.get('activityId'))}")
    print(f"  Timestamp:      {_transaction_sort_key(transaction)}")


if __name__ == "__main__":
    main()
