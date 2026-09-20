"""
Standalone script: lists every Schwab account linked to this API token,
showing the account number and its corresponding hash. Use this to figure
out which hash belongs to which account, then set ACCOUNT_HASH in
config.py to that value so the bot always targets the right one.

Run manually:
    python3 list_accounts.py
"""

import sys

import config

try:
    from schwab.auth import easy_client
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)


###################
# Returns client
###################
def get_client():
    if not config.API_KEY or not config.APP_SECRET:
        print("SCHWAB_API_KEY / SCHWAB_APP_SECRET are not set as environment variables.")
        sys.exit(1)
    client = easy_client(
        api_key=config.API_KEY,
        app_secret=config.APP_SECRET,
        callback_url=config.CALLBACK_URL,
        token_path=config.TOKEN_PATH,
    )
    return client


def main():
    client = get_client()

    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()

    if not accounts:
        print("No linked accounts found for this token.")
        return

    print(f"Found {len(accounts)} linked account(s):\n")

    for i, acct in enumerate(accounts, start=1):
        account_number = acct.get("accountNumber", "?")
        account_hash = acct.get("hashValue", "?")

        # Pull balances/type so you can identify it by more than just the
        # number -- e.g. "Individual" vs "Roth IRA" vs the account's cash
        # balance, all useful for telling two accounts apart at a glance.
        detail_resp = client.get_account(account_hash)
        account_type = "?"
        cash_balance = "?"
        if detail_resp.status_code == 200:
            detail = detail_resp.json()
            securities_account = detail.get("securitiesAccount", {})
            account_type = securities_account.get("type", "?")
            balances = securities_account.get("currentBalances", {})
            cash_balance = balances.get("cashBalance", "?")

        print(f"[{i}] Account Number: {account_number}")
        print(f"    Account Hash:   {account_hash}")
        print(f"    Type:           {account_type}")
        print(f"    Cash Balance:   {cash_balance}")
        print()

    print("Once you know which one you want, copy its Account Hash into")
    print("config.py:  ACCOUNT_HASH = \"<hash here>\"")


if __name__ == "__main__":
    main()
