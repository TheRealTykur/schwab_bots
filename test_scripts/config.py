"""
Configuration for the Schwab rebalance bot.
Edit the values below. Nothing here talks to the network.
"""

import os

# --- Strategy settings -------------------------------------------------------
# Target allocation as a fraction of TOTAL account value (cash + all three
# positions). These should sum to 1.0.
TARGETS = {
    "SCHD": 0.15,
    "SCHG": 0.55,
    "SWPPX": 0.30,
}

SYMBOL = "VOO"                # the single ticker you're dollar-cost-averaging into
DAILY_SHARE_QUANTITY = 1       # fixed number of whole shares to buy each trading day
CASH_BUFFER_MULTIPLIER = 1.05  # Used to prevent account Cash from getting to low

# If your token has more than one linked account, run list_accounts.py to
# see each account's hash, then paste the correct one here. Leave blank to
# fall back to whichever account get_account_numbers() returns first --
# NOT safe to rely on if you have multiple accounts.

# --- Schwab API credentials -------------------------------------------------
# Create an app at https://developer.schwab.com to get these.
# Do NOT hardcode real values here in a file you might commit to git.
# Store them as environment variables instead and read them like this:
API_KEY = os.environ.get("SCHWAB_API_KEY", "")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.environ.get("SCHWAB_CALLBACK_URL", "https://127.0.0.1:8182")

ACCOUNT_HASH = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# Where schwab-py will cache your OAuth token after the one-time browser login.
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "schwab_token.json")

# --- Safety rails -------------------------------------------------------------
DRY_RUN = True                 # True = log what would happen, place NO real orders

# --- Bookkeeping --------------------------------------------------------------
LOG_PATH = os.path.join(os.path.dirname(__file__), "test_scrips.log")

# The "Date" logged for each buy is computed in this timezone explicitly,
# rather than relying on the machine's system timezone being set correctly
# (a real bug we hit: a fresh Raspberry Pi OS install can default to UTC,
# which shifts the calendar date near midnight local time). Use an IANA
# timezone name, e.g. "America/New_York".
LOCAL_TIMEZONE = "America/New_York"