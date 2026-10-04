from unittest.mock import Mock, patch

import pytest

from support import accounts as account


def test_get_hash_uses_configured_hash_without_api_call():
    client = Mock()

    assert account.get_hash(client, "configured-hash") == "configured-hash"
    client.get_account_numbers.assert_not_called()


def test_get_hash_uses_first_account_when_not_configured():
    client = Mock()
    client.get_account_numbers.return_value.json.return_value = [
        {"accountNumber": "123", "hashValue": "hash-123"},
        {"accountNumber": "456", "hashValue": "hash-456"},
    ]
    log = Mock()

    assert account.get_hash(client, "", log) == "hash-123"
    log.warning.assert_called_once()


def test_get_hash_does_not_warn_for_single_account():
    client = Mock()
    client.get_account_numbers.return_value.json.return_value = [
        {"accountNumber": "123", "hashValue": "hash-123"},
    ]
    log = Mock()

    assert account.get_hash(client, "", log) == "hash-123"
    log.warning.assert_not_called()


def test_get_hash_raises_when_no_accounts():
    client = Mock()
    client.get_account_numbers.return_value.json.return_value = []

    with pytest.raises(RuntimeError, match="No linked Schwab accounts"):
        account.get_hash(client)


def test_get_client_uses_master_config():
    with patch.object(account.master_config, "API_KEY", "api-key"),          patch.object(account.master_config, "APP_SECRET", "app-secret"),          patch.object(account, "easy_client", return_value="client") as easy_client:
        assert account.get_client() == "client"

    easy_client.assert_called_once_with(
        api_key="api-key",
        app_secret="app-secret",
        callback_url=account.master_config.CALLBACK_URL,
        token_path=account.master_config.TOKEN_PATH,
    )
