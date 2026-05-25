import logging

import anthropic
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, anthropic.APIConnectionError):
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code in (429, 529):
        return True
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def retried_invoke(chain, inputs: dict):
    """Call chain.invoke(inputs) with exponential-backoff retry on 429/529 and connection errors."""
    return chain.invoke(inputs)
