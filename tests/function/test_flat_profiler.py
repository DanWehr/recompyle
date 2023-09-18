import logging
import time
from collections.abc import Callable

import pytest

from recompyle import flat_profile

last_total: float = None
last_limit: float = None
last_times: dict = None
last_func: Callable = None


def get_args(total: float, limit: float, times: dict, func: Callable):
    """Instead of default logging, capture values for test comparison."""
    global last_total
    global last_limit
    global last_times
    global last_func
    last_total = total
    last_limit = limit
    last_times = times
    last_func = func


@pytest.fixture()
def _wipe_args():
    global last_total
    global last_limit
    global last_times
    global last_func
    yield
    last_total = None
    last_limit = None
    last_times = None
    last_func = None


def delay_func(delay_time: float):
    time.sleep(delay_time)


@flat_profile(time_limit=0.2, below_callback=get_args, above_callback=None)
def custom_below_callback(delay_time: float):
    delay_func(delay_time)
    return sum(int(x) for x in range(3))


@flat_profile(time_limit=0.2, below_callback=None, above_callback=get_args)
def custom_above_callback(delay_time: float):
    delay_func(delay_time)
    return sum(int(x) for x in range(3))


@flat_profile(time_limit=0.2)
def default_callbacks(delay_time: float):
    delay_func(delay_time)
    return sum(int(x) for x in range(3))


@pytest.mark.usefixtures("_wipe_args")
class TestFlatProfiler:
    def verify_callback_args(self, func_name, limit):
        """Helper function that checks all times were recorded that should have been."""
        delay_times = last_times.pop("delay_func")
        assert len(delay_times) == 1
        sum_times = last_times.pop("sum")
        assert len(sum_times) == 1
        range_times = last_times.pop("range")
        assert len(range_times) == 1
        int_times = last_times.pop("int")
        assert len(int_times) == 3
        assert not last_times
        assert last_func.__name__ == func_name
        assert last_limit == limit

    def test_custom_below(self):
        """Custom callback is used when below the limit."""
        assert custom_below_callback(0.1) == 3
        self.verify_callback_args("custom_below_callback", 0.2)
        assert last_total < last_limit

    def test_custom_below_norun(self):
        """No below callback run when above limit and above is None."""
        assert custom_below_callback(0.3) == 3
        assert last_total is None
        assert last_limit is None
        assert last_times is None
        assert last_func is None

    def test_custom_above(self):
        """Custom callback is used when above the limit."""
        assert custom_above_callback(0.3) == 3
        self.verify_callback_args("custom_above_callback", 0.2)
        assert last_total > last_limit

    def test_custom_above_norun(self):
        """No above callback run when below limit and below is None."""
        assert custom_above_callback(0.1) == 3
        assert last_total is None
        assert last_limit is None
        assert last_times is None
        assert last_func is None

    def test_default_below(self, caplog):
        """Default callback is used when below the limit."""
        with caplog.at_level(logging.INFO):
            assert default_callbacks(delay_time=0.1) == 3
        assert len(caplog.records) == 1
        assert "below limit" in caplog.records[0].message
        assert "delay_func" not in caplog.records[0].message  # Log doesn't have call info.

    def test_default_above(self, caplog):
        """Default callback is used when above the limit."""
        with caplog.at_level(logging.INFO):
            assert default_callbacks(delay_time=0.3) == 3
        assert len(caplog.records) == 1
        assert "above limit" in caplog.records[0].message
        assert "delay_func" in caplog.records[0].message  # Log has call info.
