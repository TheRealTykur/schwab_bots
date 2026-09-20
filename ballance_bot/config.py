"""
Configuration for the Schwab rebalance bot.
Edit the values below. Nothing here talks to the network.
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import Master_Config

# --- Strategy settings -------------------------------------------------------
# Target allocation as a fraction of TOTAL account value (cash + all three
# positions). These should sum to 1.0.
TARGETS = {
    "SCHD": 0.15,
    "SCHG": 0.55,
    "SWPPX": 0.30,
}

# If your token has more than one linked account, run list_accounts.py to
# see each account's hash, then paste the correct one here. Leave blank to
# fall back to whichever account get_account_numbers() returns first --
# NOT safe to rely on if you have multiple accounts.
ACCOUNT_HASH = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# --- Safety rails -------------------------------------------------------------
DRY_RUN = True                 # True = log what would happen, place NO real orders

# --- Bookkeeping --------------------------------------------------------------
LOG_PATH = os.path.join(os.path.dirname(__file__), "rebalance_log.txt")

