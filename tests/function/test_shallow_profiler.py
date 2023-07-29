import logging
import time
from collections.abc import Callable

import pytest

from recompyle import shallow_call_profiler

log = logging.getLogger(__name__)

last_total: float = None
last_limit: float = None
last_times: dict = None
last_func: Callable = None


def get_times(total: float, limit: float, times: dict, func: Callable):
    """Instead of default logging, capture values for test comparison."""
    global last_total
    global last_limit
    global last_times
    global last_func
    last_total = total
    last_limit = limit
    last_times = times
    last_func = func


def delay_func():
    time.sleep(.5)


@shallow_call_profiler(time_limit=1, under_callback=get_times)
def below_limit():
    delay_func()
    return sum(int(x) for x in range(3))


@shallow_call_profiler(time_limit=0.3, over_callback=get_times)
def above_limit():
    delay_func()
    return sum(int(x) for x in range(3))


class TestShallowCallProfiler:
    def verify_time_structure(self):
        delay_times = last_times.pop("delay_func")
        assert len(delay_times) == 1
        sum_times = last_times.pop("sum")
        assert len(sum_times) == 1
        range_times = last_times.pop("range")
        assert len(range_times) == 1
        int_times = last_times.pop("int")
        assert len(int_times) == 3
        assert not last_times

    def test_below_limit(self):
        assert below_limit() == 3
        self.verify_time_structure()
        assert last_func.__name__ == "below_limit"
        assert last_limit == 1
        assert last_total < last_limit

    def test_above_limit(self):
        assert above_limit() == 3
        self.verify_time_structure()
        assert last_func.__name__ == "above_limit"
        assert last_limit == 0.3
        assert last_total > last_limit
