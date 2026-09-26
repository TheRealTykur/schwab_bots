from unittest.mock import Mock

from support import market_data


def test_get_current_price(fake_response):
    client = Mock()
    client.get_quote.return_value = fake_response({
        "VOO": {"quote": {"lastPrice": 512.34}}
    })

    assert market_data.get_current_price(client, "VOO") == 512.34
    client.get_quote.assert_called_once_with("VOO")


def test_get_current_prices(fake_response):
    client = Mock()
    client.get_quotes.return_value = fake_response({
        "VOO": {"quote": {"lastPrice": 512.34}},
        "SCHD": {"quote": {"lastPrice": 27.12}},
    })

    assert market_data.get_current_prices(client, ["VOO", "SCHD"]) == {
        "VOO": 512.34,
        "SCHD": 27.12,
    }


def test_get_positions_calculates_net_quantity(fake_response):
    client = Mock()
    client.Account.Fields.POSITIONS = "POSITIONS"
    client.get_account.return_value = fake_response({
        "securitiesAccount": {
            "positions": [
                {
                    "instrument": {"symbol": "VOO"},
                    "longQuantity": 10,
                    "shortQuantity": 2,
                    "marketValue": 5000,
                }
            ]
        }
    })

    assert market_data.get_positions(client, "hash") == [
        {"symbol": "VOO", "quantity": 8, "market_value": 5000}
    ]


def test_get_positions_returns_empty_when_no_positions(fake_response):
    client = Mock()
    client.Account.Fields.POSITIONS = "POSITIONS"
    client.get_account.return_value = fake_response({"securitiesAccount": {}})

    assert market_data.get_positions(client, "hash") == []


def test_is_market_open_returns_true_when_any_equity_product_is_open(fake_response):
    client = Mock()
    client.MarketHours.Market.EQUITY = "EQUITY"
    client.get_market_hours.return_value = fake_response({
        "equity": {
            "EQ": {"isOpen": True}
        }
    })

    assert market_data.is_market_open(client) is True


def test_is_market_open_returns_false_when_market_is_closed(fake_response):
    client = Mock()
    client.MarketHours.Market.EQUITY = "EQUITY"
    client.get_market_hours.return_value = fake_response({
        "equity": {
            "EQ": {"isOpen": False}
        }
    })

    assert market_data.is_market_open(client) is False
