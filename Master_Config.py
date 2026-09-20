"""
Master Configuration used in all bots.
"""

import os

# --- Schwab API credentials -------------------------------------------------
# Create an app at https://developer.schwab.com to get these.
# Do NOT hardcode real values here in a file you might commit to git.
# Store them as environment variables instead and read them like this:
API_KEY = os.environ.get("SCHWAB_API_KEY", "")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.environ.get("SCHWAB_CALLBACK_URL", "https://127.0.0.1:8182")

# Where schwab-py will cache your OAuth token after the one-time browser login.
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "schwab_token.json")

# The "Date" logged for each buy is computed in this timezone explicitly,
# rather than relying on the machine's system timezone being set correctly
# (a real bug we hit: a fresh Raspberry Pi OS install can default to UTC,
# which shifts the calendar date near midnight local time). Use an IANA
# timezone name, e.g. "America/New_York".
LOCAL_TIMEZONE = "America/New_York"


