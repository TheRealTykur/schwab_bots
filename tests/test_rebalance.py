from unittest.mock import Mock, patch

from bots.balance import bot
from bots.balance import config


def test_plan_buys_returns_empty_for_zero_account_value():
    assert bot.plan_buys(
        0,
        {"SCHD": 0, "SCHG": 0, "SWPPX": 0},
        {"SCHD": 100, "SCHG": 100, "SWPPX": 100},
    ) == {}


def test_plan_buys_returns_empty_when_positions_are_at_target():
    position_values = {
        "SCHD": 1500,
        "SCHG": 5500,
        "SWPPX": 3000,
    }
    prices = {"SCHD": 100, "SCHG": 100, "SWPPX": 100}

    assert bot.plan_buys(0, position_values, prices) == {}


def test_plan_buys_never_spends_more_than_available_cash():
    cash = 250
    position_values = {"SCHD": 1000, "SCHG": 1000, "SWPPX": 1000}
    prices = {"SCHD": 100, "SCHG": 100, "SWPPX": 100}

    result = bot.plan_buys(cash, position_values, prices)
    total_cost = sum(result[ticker] * prices[ticker] for ticker in result)

    assert total_cost <= cash


def test_plan_buys_only_buys_underweight_securities():
    position_values = {
        "SCHD": 1500,
        "SCHG": 7000,
        "SWPPX": 1500,
    }
    prices = {"SCHD": 100, "SCHG": 100, "SWPPX": 100}

    result = bot.plan_buys(0, position_values, prices)

    assert result == {}


def test_plan_buys_prefers_largest_allocation_gap():
    position_values = {
        "SCHD": 500,
        "SCHG": 5000,
        "SWPPX": 2500,
    }
    prices = {"SCHD": 100, "SCHG": 100, "SWPPX": 100}

    result = bot.plan_buys(100, position_values, prices)

    assert result == {"SCHD": 1}


def test_plan_buys_skips_unaffordable_underweight_security():
    position_values = {
        "SCHD": 500,
        "SCHG": 5000,
        "SWPPX": 2500,
    }
    prices = {"SCHD": 1000, "SCHG": 100, "SWPPX": 100}

    result = bot.plan_buys(100, position_values, prices)

    assert "SCHD" not in result


def test_rebalance_place_buy_dry_run_does_not_submit_order():
    client = Mock()

    with patch.object(config, "DRY_RUN", True):
        assert bot.place_buy(client, "hash", "SCHG", 2, 100.0) is True

    client.place_order.assert_not_called()


def test_rebalance_place_buy_live_mode_submits_order():
    client = Mock()
    response = Mock(status_code=201)
    client.place_order.return_value = response
    order = object()

    with patch.object(config, "DRY_RUN", False), patch.object(
        bot, "equity_buy_market", return_value=Mock(build=Mock(return_value=order))
    ) as buy_market:
        assert bot.place_buy(client, "hash", "SCHG", 2, 100.0) is True

    buy_market.assert_called_once_with("SCHG", 2)
    client.place_order.assert_called_once_with("hash", order)
    response.raise_for_status.assert_called_once()


def test_rebalance_get_account_hash_uses_configured_hash():
    client = Mock()

    with patch.object(config, "ACCOUNT_HASH", "configured-hash"):
        assert bot.get_account_hash(client) == "configured-hash"

    client.get_account_numbers.assert_not_called()
