import time

import pytest
from evernote.edam.error.ttypes import EDAMSystemException

from src import fetcher


def test_with_retry_rate_limit(monkeypatch):
    calls = {"n": 0}

    def fake_sleep(_):
        return None

    monkeypatch.setattr(time, "sleep", fake_sleep)

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            exc = EDAMSystemException()
            exc.errorCode = 19
            exc.rateLimitDuration = 0
            raise exc
        return "ok"

    assert fetcher._with_retry(flaky, retries=3) == "ok"


def test_with_retry_other_error(monkeypatch):
    def fake_sleep(_):
        return None

    monkeypatch.setattr(time, "sleep", fake_sleep)

    def fail():
        exc = EDAMSystemException()
        exc.errorCode = 1
        raise exc

    with pytest.raises(EDAMSystemException):
        fetcher._with_retry(fail, retries=2)
