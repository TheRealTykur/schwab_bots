from unittest.mock import Mock, patch

import pytest

from support import statistical_metrics as metrics


def test_get_moving_average():
    with patch.object(metrics, "_get_daily_closes", return_value=[10, 20, 30, 40, 50]):
        assert metrics.get_moving_average(Mock(), "VOO", 5) == 30


def test_get_percent_from_high():
    client = Mock()
    with patch.object(metrics, "_get_daily_closes", return_value=[100, 110, 120]), \
         patch.object(metrics.market_data, "get_current_price", return_value=108):
        assert metrics.get_percent_from_high(client, "VOO", 3) == pytest.approx(-10.0)


def test_get_percent_change():
    client = Mock()
    with patch.object(metrics, "_get_daily_closes", return_value=[100, 105, 110]), \
         patch.object(metrics.market_data, "get_current_price", return_value=110):
        assert metrics.get_percent_change(client, "VOO", "week") == pytest.approx(10.0)


def test_get_percent_change_rejects_invalid_period():
    with pytest.raises(ValueError, match="period must be one of"):
        metrics.get_percent_change(Mock(), "VOO", "day")


def test_get_day_change(fake_response):
    client = Mock()
    client.get_quote.return_value = fake_response({
        "VOO": {
            "quote": {
                "lastPrice": 110,
                "closePrice": 100,
            }
        }
    })

    assert metrics.get_day_change(client, "VOO") == pytest.approx(10.0)


def test_get_rsi_returns_100_when_all_changes_are_positive():
    closes = [100, 101, 102, 103, 104]

    with patch.object(metrics, "_get_daily_closes", return_value=closes):
        assert metrics.get_rsi(Mock(), "VOO", period=4) == 100.0


def test_get_rsi_calculates_mixed_changes():
    closes = [100, 110, 100, 110, 100]

    with patch.object(metrics, "_get_daily_closes", return_value=closes):
        assert metrics.get_rsi(Mock(), "VOO", period=4) == pytest.approx(50.0)


def test_detect_ma_crossover_returns_golden_cross():
    with patch.object(metrics, "get_moving_average", side_effect=[120, 100]):
        assert metrics.detect_ma_crossover(Mock(), "VOO", 50, 200) == "golden_cross"


def test_detect_ma_crossover_returns_death_cross():
    with patch.object(metrics, "get_moving_average", side_effect=[90, 100]):
        assert metrics.detect_ma_crossover(Mock(), "VOO", 50, 200) == "death_cross"


def test_detect_ma_crossover_returns_no_crossover_data_when_equal():
    with patch.object(metrics, "get_moving_average", side_effect=[100, 100]):
        assert metrics.detect_ma_crossover(Mock(), "VOO", 50, 200) == "no_crossover_data"


def test_get_daily_closes_raises_when_history_is_too_short(fake_response):
    client = Mock()
    client.get_price_history_every_day.return_value = fake_response({
        "candles": [{"close": 100}, {"close": 101}]
    })

    with pytest.raises(ValueError, match="need 5"):
        metrics._get_daily_closes(client, "VOO", 5)
