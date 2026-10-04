"""
Setup script: runs just the Schwab OAuth login flow and saves the
resulting token file. This does NOT fetch quotes, account data, or place
any orders -- it exists so you can do the browser login step on its own,
without running the full bot.

Run this once a week to keep token fresh idealy on Sundays (on a machine with a browser -- see README):
    python3 setup_schwab_auth_token.py

If schwab_token.json already exists and is still valid, this just confirms
it works instead of re-triggering the browser login.
"""
import os
import sys
from config import master as master_config

from support.accounts import get_client


def main():
    print("Setting up Schwab authentication...")
    print(f"Token will be saved to: {master_config.TOKEN_PATH}\n")

    if os.path.exists(master_config.TOKEN_PATH):
        os.remove(master_config.TOKEN_PATH)
        print("Old schwab_token.json deleted successfully. Continuing with token generation")
    else:
        print("The schwab_token does not yet exist. Continuing with token generation")

    client = get_client()

    resp = client.get_account_numbers()
    resp.raise_for_status()
    accounts = resp.json()

    print("\nSuccess. Authentication is working.")
    print(f"Found {len(accounts)} linked account(s).")
    print(f"Token saved at: {master_config.TOKEN_PATH}")
    print("\nIf this ran on your laptop/desktop, copy schwab_token.json over")
    print("to the Pi now (into the same folder as config.py there).")


if __name__ == "__main__":
    main()
