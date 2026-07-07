import logging
import time

import requests

logger = logging.getLogger(__name__)


def get_with_retry(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    max_retries: int = 3,
    backoff_base: float = 1.5,
    timeout: float = 15.0,
) -> requests.Response:
    """GET com backoff exponencial. Lança a última exceção se todas as tentativas falharem."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            sleep_for = backoff_base**attempt
            logger.warning(
                "GET %s falhou (tentativa %d/%d): %s — aguardando %.1fs",
                url, attempt + 1, max_retries, exc, sleep_for,
            )
            if attempt < max_retries - 1:
                time.sleep(sleep_for)
    assert last_exc is not None
    raise last_exc
