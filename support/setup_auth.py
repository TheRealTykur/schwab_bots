"""
Setup script: runs just the Schwab OAuth login flow and saves the
resulting token file. This does NOT fetch quotes, account data, or place
any orders -- it exists so you can do the browser login step on its own,
without running the full bot.

Run this once a week to keep token fresh idealy on Sundays (on a machine with a browser -- see README):
    python3 setup_auth.py

If schwab_token.json already exists and is still valid, this just confirms
it works instead of re-triggering the browser login.
"""

import sys
import config

try:
    from schwab.auth import easy_client
except ImportError:
    print("schwab-py is not installed. Run: pip install schwab-py")
    sys.exit(1)


def get_client():
    if not config.API_KEY or not config.APP_SECRET:
        print("SCHWAB_API_KEY / SCHWAB_APP_SECRET are not set as environment variables.")
        sys.exit(1)
    return easy_client(
        api_key=config.API_KEY,
        app_secret=config.APP_SECRET,
        callback_url=config.CALLBACK_URL,
        token_path=config.TOKEN_PATH,
    )


def main():
    print("Setting up Schwab authentication...")
    print(f"Token will be saved to: {config.TOKEN_PATH}\n")

    client = get_client()

    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()

    print("\nSuccess. Authentication is working.")
    print(f"Found {len(accounts)} linked account(s).")
    print(f"Token saved at: {config.TOKEN_PATH}")
    print("\nIf this ran on your laptop/desktop, copy schwab_token.json over")
    print("to the Pi now (into the same folder as config.py there).")


if __name__ == "__main__":
    main()
