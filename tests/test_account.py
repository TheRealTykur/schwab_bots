from unittest.mock import Mock

from support import account


def test_get_cash_balance_reads_cash_balance(fake_response):
    client = Mock()
    client.get_account.return_value = fake_response({
        "securitiesAccount": {
            "currentBalances": {"cashBalance": 1234.56}
        }
    })

    assert account.get_cash_balance(client, "hash") == 1234.56
    client.get_account.assert_called_once_with("hash")


def test_get_cash_balance_defaults_to_zero(fake_response):
    client = Mock()
    client.get_account.return_value = fake_response({"securitiesAccount": {}})

    assert account.get_cash_balance(client, "hash") == 0.0


def test_get_position_quantity_returns_position_quantity(monkeypatch):
    monkeypatch.setattr(account.market_data, "get_positions", lambda client, account_hash: [
        {"symbol": "VOO", "quantity": 3, "market_value": 1500},
    ])

    assert account.get_position_quantity(Mock(), "hash", "VOO") == 3


def test_get_position_quantity_returns_zero_when_not_held(monkeypatch):
    monkeypatch.setattr(account.market_data, "get_positions", lambda client, account_hash: [])

    assert account.get_position_quantity(Mock(), "hash", "VOO") == 0


def test_get_portfolio_value_reads_liquidation_value(fake_response):
    client = Mock()
    client.get_account.return_value = fake_response({
        "securitiesAccount": {
            "currentBalances": {"liquidationValue": 9876.54}
        }
    })

    assert account.get_portfolio_value(client, "hash") == 9876.54


def test_get_account_snapshot_returns_cash_and_requested_positions(fake_response):
    client = Mock()
    client.Account.Fields.POSITIONS = "POSITIONS"
    client.get_account.return_value = fake_response({
        "securitiesAccount": {
            "currentBalances": {"cashBalance": 5000},
            "positions": [
                {
                    "instrument": {"symbol": "VOO"},
                    "marketValue": 2500,
                },
                {
                    "instrument": {"symbol": "SCHD"},
                    "marketValue": 1000,
                },
                {
                    "instrument": {"symbol": "OTHER"},
                    "marketValue": 9999,
                },
            ],
        }
    })

    cash, positions = account.get_account_snapshot(
        client, "hash", ["VOO", "SCHD", "SWPPX"]
    )

    assert cash == 5000.0
    assert positions == {"VOO": 2500.0, "SCHD": 1000.0, "SWPPX": 0.0}
    client.get_account.assert_called_once_with("hash", fields=["POSITIONS"])
