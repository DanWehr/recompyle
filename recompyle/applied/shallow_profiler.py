import functools
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from operator import itemgetter
from pprint import pformat
from typing import ParamSpec, TypeVar

from recompyle.rewrite import rewrite_wrap_calls_func

log = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def shallow_call_profiler(*, time_limit: float = 1.0) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator factory for profiling the wrapped function."""
    _call_times: defaultdict[str, list[float]] = defaultdict(list)

    def _collect_sorted_times():
        """Write call time summary to log."""
        sum_times = ((func_str, sum(times)) for func_str, times in _call_times.items())
        sum_times = (
            f"{func_str}: {time:.3f}s" for func_str, time in sorted(sum_times, key=itemgetter(1), reverse=True)
        )
        return sum_times

    def _record_call_time(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Wrapper to record execution time of inner calls."""
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
        except Exception:
            raise
        finally:
            end = time.monotonic()
            _call_times[func.__qualname__].append(end - start)
        return result

    def _measure_calls(func: Callable[P, T]) -> Callable[P, T]:
        """Decorator to measure total call time and inner call times."""
        _new_func = rewrite_wrap_calls_func(
            target_func=func, wrap_call=_record_call_time, decorator_name="shallow_call_profiler",
        )

        @functools.wraps(func)
        def inner_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time.monotonic()
            try:
                return _new_func(*args, **kwargs)
            finally:
                duration = time.monotonic() - start
                log_str = f"{func.__qualname__} took {duration:.3f}s to run, {{s}} the {time_limit}s limit."
                if duration < time_limit:
                    log.info(log_str.format(s="below"))
                else:
                    times = _collect_sorted_times()
                    log.info(log_str.format(s="above") + f"\n{pformat(tuple(times))}")
                _call_times.clear()
        return inner_wrapper
    return _measure_calls
