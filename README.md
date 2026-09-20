# Schwab Dollar Cost Average Bot

Runs once a day. Buys a fixed quantity of one ticker every trading
day.

**This places real trades with real money once you turn off `DRY_RUN`.
Read this whole file before you do that.**

Use case.  Charles Schwab allows for recurring investments into Mutual Funds, but not 
into Exchange-Traded Funds (ETF).  This bot is used for a niche of Dollar Cost Averaging
into a low-cost ETF.

## 1. Get Schwab API credentials

1.  Go to https://developer.schwab.com and create a developer account.
2.  Register an app requesting the "Accounts and Trading" and "Market
    Data" products. Schwab has to approve this. It can take a few days.
3.  Set a callback URL, e.g., `https://127.0.0.1:8182` (must use https,
    even for localhost).
4.  Once approved, you'll get an API Key (client ID) and App Secret.

## 2. Set environment variables

Don't put real credentials in `config.py`.

``` bash
export SCHWAB_API_KEY="your-api-key"
export SCHWAB_APP_SECRET="your-app-secret"
export SCHWAB_CALLBACK_URL="https://127.0.0.1:8182"
```

These variables will apply to the current shell session. If you want
them to be available automatically in future terminal sessions, add the
`export` commands to your shell startup file, such as `~/.bashrc` or
`~/.zshrc`, and then restart your terminal or run:

``` bash
source ~/.bashrc
```

If the bot will be run by `cron`, make sure the environment variables
are available to the cron job as well.

## 3. Install dependencies

``` bash
python3 -m pip install -r requirements.txt
```

## 4. First run: one-time browser login

The first time you run the bot, `schwab-py` will open a browser window
and ask you to log into Schwab and authorize the app.

After that, it caches a refresh token in `schwab_token.json` next to the
script, and future runs are non-interactive, which is what makes
scheduling possible.

Run it manually once:

``` bash
python3 schwab_bot.py
```

Do this with `DRY_RUN = True` (the default in `config.py`) so no real
orders get placed while you're testing the auth flow.

## 5. Edit config.py

Open `config.py` and set:

-   `SYMBOL` - the ticker to buy
-   `DAILY_SHARE_QUANTITY` - fixed number of whole shares to buy each
    day
-   `CASH_BUFFER_MULTIPLIER` - fixed percentage to not let the bot place
    if the cash position falls too low.

**If more than one Schwab account is linked to this API token**, run:

``` bash
python3 list_accounts.py
```

This prints each linked account's number, hash, type, and cash balance
so you can tell them apart.

Copy the hash of the one you want the bot to use into `config.py`:

``` python
ACCOUNT_HASH = "the-hash-you-copied"
```

If you leave `ACCOUNT_HASH` blank and have multiple accounts, the bot
defaults to whichever one `get_account_numbers()` happens to return
first. Do not rely on this if it matters which account gets used.

## 6. WIP schwab_utils

This is a file that is being worked on to expand the future abilities of 
bots in this project.  

### ideas for the future 
- ballance bot
- add more functionality to DCA bot
- add in db support
- add in a locally hosted website view dashboards