# Schwab Bots

A small Python project containing automated Schwab trading bots.

The repository currently contains:

- **DCA bot**: buys a configured number of shares of one ticker.
- **Rebalance bot**: buys underweight securities based on configured target allocations.
- **Shared configuration**: Schwab API credentials, callback URL, token location, and timezone.
- **Support code**: shared account and market-data utilities.
- **Test scripts**: tools for checking authentication and linked Schwab accounts.

> **Warning:** These bots can place real trades. Keep `DRY_RUN = True` while you set up and test.

---

## 1. Get Schwab API Credentials

Create a Schwab Developer account:

https://developer.schwab.com/

Create/register an application with:

- **Accounts and Trading**
- **Market Data**

Use this callback URL:

```text
https://127.0.0.1:8182
```

The callback URL must use `https`, even though it points to localhost.

Once the application is approved, Schwab provides:

- **App Key / API Key**
- **App Secret**

Use these as environment variables rather than hardcoding them in the Python code.

---

## 2. Set Up the Environment on Unix / Linux

From the repository root, export the Schwab credentials:

```bash
export SCHWAB_API_KEY="your-api-key"
export SCHWAB_APP_SECRET="your-app-secret"
export SCHWAB_CALLBACK_URL="https://127.0.0.1:8182"
```

These variables only apply to the current shell session.

For persistent environment variables, add them to your shell configuration file, such as:

```bash
~/.bashrc
```

or:

```bash
~/.zshrc
```

Then reload the configuration:

```bash
source ~/.bashrc
```

Do not commit your credentials to Git.

---

## 3. Install Dependencies

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
python3 -m pip install -r requirements.txt
```

If the virtual environment is already active, this is sufficient:

```bash
pip install -r requirements.txt
```

---

## 4. Get the Schwab Token

The project uses `schwab-py` to handle Schwab authentication.

First, make sure the token directory exists:

```bash
mkdir -p config/tokens
```

Then run:

```bash
python3 config/setup_auth.py
```

The authentication process will open the Schwab authorization flow.

After authorization, the OAuth token is stored at:

```text
config/tokens/schwab_token.json
```

The bots use this token for subsequent Schwab API requests.

The token file should **not** be committed to Git.

Authentication needs to be repeated once a week; delete the schwab_token on Sundays and run the setup script again.

---

## 5. Configure the Bots

### DCA Bot

Configuration:

```text
bots/dca/config.py
```

The main settings are:

```python
SYMBOL = "VOO"
DAILY_SHARE_QUANTITY = 1
CASH_BUFFER_MULTIPLIER = 1.05
ACCOUNT_HASH = ""
DRY_RUN = True
```

Change these for your account and strategy.

### `SYMBOL`

The ticker the DCA bot will purchase.

Example:

```python
SYMBOL = "VOO"
```

### `DAILY_SHARE_QUANTITY`

The number of whole shares to purchase each time the bot runs.

Example:

```python
DAILY_SHARE_QUANTITY = 1
```

### `CASH_BUFFER_MULTIPLIER`

Adds a cash buffer above the estimated order cost.

The default is:

```python
CASH_BUFFER_MULTIPLIER = 1.05
```

### `ACCOUNT_HASH`

The Schwab account hash to trade in.

If you have multiple Schwab accounts, set this explicitly.

You can use:

```bash
python3 test_scripts/list_accounts.py
```

to see the accounts and account hashes available to the authenticated user.

### `DRY_RUN`

Keep this set to:

```python
DRY_RUN = True
```

while testing.

Change it to:

```python
DRY_RUN = False
```

Only when you are ready for the bot to submit real orders.

---

## 6. Rebalance Bot Configuration

Configuration:

```text
bots/ballance/config.py
```

The target allocations are configured in:

```python
TARGETS = {
    "SCHD": 0.15,
    "SCHG": 0.55,
    "SWPPX": 0.30,
}
```

Change the securities and percentages to match the portfolio you want the bot to target.

The allocations should total:

```text
1.00
```

The rebalance bot is currently **buy-only**. It does not sell positions to bring them back to target.

Keep:

```python
DRY_RUN = True
```

until the strategy has been tested.

---

## 7. Running the Bots

From the repository root, the intended package-style commands are:

```bash
python3 -m bots.dca.bot
```

and:

```bash
python3 -m bots.ballance.bot
```

The bots do not contain their own scheduler.

For automated execution on Unix/Linux, use something such as:

- `cron`
- `systemd`
- another process scheduler

Make sure the bot is only invoked as often as intended. The DCA bot does not currently prevent multiple executions on the same day.

Example cron job:
```crontab
31 9 * * 1-5 cd /home/schwab_bots && . /home/.schwab_env && /usr/bin/python3 -m bots.<bot to run>.bot
```
---

# Work in Progress

The following items were identified during the code review and still need to be addressed.

- [ ] **Fix the diagnostic script**
  - `test_scripts/schwab_utils_test.py` references `su`, but `su` is not defined.

- [ ] **Rename `ballance` to `balance`**
  - The directory is currently spelled `ballance`.
     
- [ ] **Add Empty Dir in config**
  - Did not commit the empty dir in the last push.

- [ ] **Clean up duplicated configuration**
  - `test_scripts/config.py` contains configuration that overlaps with `config/master.py`.

- [ ] **Centralize authentication configuration**
  - Make the test scripts use the same master configuration as the production bots.

- [ ] **Improve `setup_auth.py`**
  - Standardize its package imports with the rest of the project.

- [ ] **Add automated tests**
  - Particularly for the rebalance allocation logic and order-planning behavior.

- [ ] **Add Database Support**
  - Add writing to a PostgreSQL database
