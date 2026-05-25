from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.retry_utils import _is_retryable, retried_invoke


def _api_status_error(status_code: int) -> anthropic.APIStatusError:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return anthropic.APIStatusError("error", response=mock_response, body={})


class TestIsRetryable:
    def test_connection_error_is_retryable(self):
        err = anthropic.APIConnectionError(request=MagicMock())
        assert _is_retryable(err) is True

    def test_429_is_retryable(self):
        assert _is_retryable(_api_status_error(429)) is True

    def test_529_is_retryable(self):
        assert _is_retryable(_api_status_error(529)) is True

    def test_500_is_not_retryable(self):
        assert _is_retryable(_api_status_error(500)) is False

    def test_arbitrary_exception_is_not_retryable(self):
        assert _is_retryable(ValueError("oops")) is False


class TestRetriedInvoke:
    def test_succeeds_on_first_try(self):
        chain = MagicMock()
        chain.invoke.return_value = "ok"
        assert retried_invoke(chain, {"k": "v"}) == "ok"
        chain.invoke.assert_called_once_with({"k": "v"})

    def test_retries_twice_on_529_then_succeeds(self):
        chain = MagicMock()
        error = _api_status_error(529)
        chain.invoke.side_effect = [error, error, "recovered"]

        with patch("time.sleep"):
            result = retried_invoke(chain, {"k": "v"})

        assert result == "recovered"
        assert chain.invoke.call_count == 3

    def test_non_retryable_error_raises_immediately(self):
        chain = MagicMock()
        chain.invoke.side_effect = _api_status_error(500)

        with pytest.raises(anthropic.APIStatusError):
            retried_invoke(chain, {"k": "v"})

        chain.invoke.assert_called_once()

    def test_exhausted_retries_reraises(self):
        chain = MagicMock()
        chain.invoke.side_effect = _api_status_error(529)

        with patch("time.sleep"), pytest.raises(anthropic.APIStatusError):
            retried_invoke(chain, {"k": "v"})

        assert chain.invoke.call_count == 5
