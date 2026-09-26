import sys
import types

import pytest


# Unit tests never contact Schwab. If schwab-py is not installed in the
# environment running the unit tests, provide the minimal import surface
# required by the bot modules. In a normal project environment the real
# schwab-py package is used instead.
try:
    import schwab  # noqa: F401
except ImportError:
    schwab = types.ModuleType("schwab")
    schwab_auth = types.ModuleType("schwab.auth")
    schwab_orders = types.ModuleType("schwab.orders")
    schwab_equities = types.ModuleType("schwab.orders.equities")

    schwab_auth.easy_client = lambda **kwargs: None
    schwab_equities.equity_buy_market = lambda symbol, quantity: None

    sys.modules["schwab"] = schwab
    sys.modules["schwab.auth"] = schwab_auth
    sys.modules["schwab.orders"] = schwab_orders
    sys.modules["schwab.orders.equities"] = schwab_equities


class FakeResponse:
    def __init__(self, data=None, status_code=200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._data


@pytest.fixture
def fake_response():
    return FakeResponse
