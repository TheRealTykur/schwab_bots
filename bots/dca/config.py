"""
Configuration for the Schwab daily DCA bot.
Edit the values below. Nothing here talks to the network.
"""

import os

# --- Strategy settings -------------------------------------------------------
SYMBOL = "????"                # the single ticker you're dollar-cost-averaging into
DAILY_SHARE_QUANTITY = 1       # fixed number of whole shares to buy each trading day
CASH_BUFFER_MULTIPLIER = 1.05  # Used to prevent account Cash from getting to low

# If your token has more than one linked account, run list_accounts.py to
# see each account's hash, then paste the correct one here. Leave blank to
# fall back to whichever account get_account_numbers() returns first --
# NOT safe to rely on if you have multiple accounts.
ACCOUNT_HASH = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# --- Safety rails -------------------------------------------------------------
DRY_RUN = True                 # True = log what would happen, place NO real orders

# --- Bookkeeping --------------------------------------------------------------
LOG_PATH = os.path.join(os.path.dirname(__file__), "dca_bot.log")
