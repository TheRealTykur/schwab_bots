from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from bots.dca import bot
from bots.dca import config


def test_get_account_hash_uses_configured_account_hash():
    client = Mock()
    with patch.object(config, "ACCOUNT_HASH", "configured-hash"):
        assert bot.get_account_hash(client) == "configured-hash"
    client.get_account_numbers.assert_not_called()


def test_get_account_hash_uses_first_linked_account_when_unconfigured():
    client = Mock()
    client.get_account_numbers.return_value.json.return_value = [
        {"accountNumber": "123", "hashValue": "hash-123"},
        {"accountNumber": "456", "hashValue": "hash-456"},
    ]

    with patch.object(config, "ACCOUNT_HASH", ""):
        assert bot.get_account_hash(client) == "hash-123"

    client.get_account_numbers.return_value.raise_for_status.assert_called_once()


def test_get_account_hash_raises_when_no_accounts():
    client = Mock()
    client.get_account_numbers.return_value.json.return_value = []

    with patch.object(config, "ACCOUNT_HASH", ""):
        with pytest.raises(RuntimeError, match="No linked Schwab accounts"):
            bot.get_account_hash(client)


def test_place_buy_dry_run_does_not_submit_order():
    client = Mock()

    with patch.object(config, "DRY_RUN", True):
        assert bot.place_buy(client, "hash", "VOO", 2, 500.0) is True

    client.place_order.assert_not_called()


def test_place_buy_live_mode_submits_order():
    client = Mock()
    response = Mock(status_code=201)
    client.place_order.return_value = response
    order = object()

    with patch.object(config, "DRY_RUN", False), patch.object(
        bot, "equity_buy_market", return_value=Mock(build=Mock(return_value=order))
    ) as buy_market:
        assert bot.place_buy(client, "hash", "VOO", 2, 500.0) is True

    buy_market.assert_called_once_with("VOO", 2)
    client.place_order.assert_called_once_with("hash", order)
    response.raise_for_status.assert_called_once()


def test_place_buy_retries_server_errors_then_succeeds():
    client = Mock()
    first_error = Exception("server unavailable")
    first_error.response = SimpleNamespace(status_code=500)
    second_error = Exception("server unavailable")
    second_error.response = SimpleNamespace(status_code=503)

    success = Mock(status_code=201)
    client.place_order.side_effect = [first_error, second_error, success]
    order = object()

    with patch.object(config, "DRY_RUN", False), patch.object(
        bot, "equity_buy_market", return_value=Mock(build=Mock(return_value=order))
    ), patch.object(bot.time, "sleep") as sleep:
        assert bot.place_buy(client, "hash", "VOO", 1, 100.0) is True

    assert client.place_order.call_count == 3
    assert sleep.call_count == 2
    sleep.assert_called_with(bot.RETRY_DELAY_SECONDS)


def test_place_buy_does_not_retry_client_error():
    client = Mock()
    error = Exception("bad request")
    error.response = SimpleNamespace(status_code=400)
    client.place_order.side_effect = error

    with patch.object(config, "DRY_RUN", False), patch.object(
        bot, "equity_buy_market", return_value=Mock(build=Mock(return_value=object()))
    ), patch.object(bot.time, "sleep") as sleep:
        with pytest.raises(Exception, match="bad request"):
            bot.place_buy(client, "hash", "VOO", 1, 100.0)

    client.place_order.assert_called_once()
    sleep.assert_not_called()


def test_main_skips_purchase_when_cash_is_insufficient():
    client = Mock()

    with patch.object(bot, "get_client", return_value=client), \
         patch.object(bot, "get_account_hash", return_value="hash"), \
         patch.object(bot.MarketData, "get_current_price", return_value=100.0), \
         patch.object(bot.AccountSupport, "get_cash_balance", return_value=100.0), \
         patch.object(bot, "place_buy") as place_buy:
        bot.main()

    place_buy.assert_not_called()


def test_main_places_purchase_when_cash_is_sufficient():
    client = Mock()

    with patch.object(config, "SYMBOL", "VOO"), \
         patch.object(config, "DAILY_SHARE_QUANTITY", 2), \
         patch.object(config, "CASH_BUFFER_MULTIPLIER", 1.05), \
         patch.object(bot, "get_client", return_value=client), \
         patch.object(bot, "get_account_hash", return_value="hash"), \
         patch.object(bot.MarketData, "get_current_price", return_value=100.0), \
         patch.object(bot.AccountSupport, "get_cash_balance", return_value=250.0), \
         patch.object(bot, "place_buy") as place_buy:
        bot.main()

    place_buy.assert_called_once_with(client, "hash", "VOO", 2, 100.0)
