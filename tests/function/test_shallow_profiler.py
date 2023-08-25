import logging
import time
from collections.abc import Callable

import pytest

from recompyle import shallow_call_profiler
from recompyle.applied import shallow_profiler

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


@shallow_call_profiler(time_limit=0.7, below_callback=get_args)
def override_below_callback():
    delay_func(0.5)
    return sum(int(x) for x in range(3))


@shallow_call_profiler(time_limit=0.3, above_callback=get_args)
def override_above_callback():
    delay_func(0.5)
    return sum(int(x) for x in range(3))


@shallow_call_profiler(time_limit=0.5)
def default_callbacks(delay_time: float):
    delay_func(delay_time)
    return sum(int(x) for x in range(3))


@pytest.mark.usefixtures("_wipe_args")
class TestShallowCallProfiler:
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

    def test_override_below(self):
        """Custom callback is used when below the limit."""
        assert override_below_callback() == 3
        self.verify_callback_args("override_below_callback", 0.7)
        assert last_total < last_limit

    def test_override_above(self):
        """Custom callback is used when above the limit."""
        assert override_above_callback() == 3
        self.verify_callback_args("override_above_callback", 0.3)
        assert last_total > last_limit

    def test_default_below(self, mocker, caplog):
        """Default callback is used when below the limit."""
        spy = mocker.spy(shallow_profiler, "default_below_log")
        with caplog.at_level(logging.INFO):
            assert default_callbacks(delay_time=0.3) == 3
        assert len(caplog.records) == 1
        assert "below limit" in caplog.records[0].message
        assert "delay_func" not in caplog.records[0].message

    def test_default_above(self, mocker, caplog):
        """Default callback is used when above the limit."""
        spy = mocker.spy(shallow_profiler, "default_above_log")
        with caplog.at_level(logging.INFO):
            assert default_callbacks(delay_time=0.7) == 3
        assert len(caplog.records) == 1
        assert "above limit" in caplog.records[0].message
        assert "delay_func" in caplog.records[0].message
