import functools
import logging
import time
from collections import defaultdict
from collections.abc import Callable, Generator
from operator import itemgetter
from pprint import pformat
from typing import ParamSpec, TypeAlias, TypeVar

from recompyle.rewrite import rewrite_wrap_calls_func

log = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


TimeDict: TypeAlias = dict[str, list[float]]


def _collect_sorted_times(times: TimeDict) -> Generator[str, None, None]:
    """Write call time summary to log."""
    sum_times = ((func_str, sum(times)) for func_str, times in times.items())
    return (
        f"{func_str}: {time:.3f}s" for func_str, time in sorted(sum_times, key=itemgetter(1), reverse=True)
    )


def default_under_log(total: float, limit: float, _: TimeDict, func: Callable) -> None:
    """Log function total time without call details."""
    log_str = f"{func.__qualname__} finished in {total:.3f}s, below limit of {limit:.3f}s"
    log.info(log_str)


def default_over_log(total: float, limit: float, times: TimeDict, func: Callable) -> None:
    """Log detailed call details for function that went over limit."""
    log_str = f"{func.__qualname__} finished in {total:.3f}s, above limit of {limit:.3f}s"
    log_str += f"\n{pformat(tuple(_collect_sorted_times(times)))}"
    log.info(log_str)


def _find_name(call: Callable) -> str:
    """Get name of a given callable."""
    try:
        return call.__qualname__
    except AttributeError:
        pass

    try:
        return call.__name__
    except AttributeError:
        pass

    try:
        return _find_name(call.__wrapped__)
    except AttributeError:
        return type(call).__name__


def shallow_call_profiler(
    *,
    time_limit: float,
    under_callback: Callable[[float, float, TimeDict, Callable[P, T]], None] = default_under_log,
    over_callback: Callable[[float, float, TimeDict, Callable[P, T]], None] = default_over_log,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Rewrites target function to record runtime of each call in it.

    A time limit must be provided, where one of two callback functions will be run depending on whether the total
    execution time of the function is below (exclusive) or above (inclusive) of the decorated function. By default
    simple INFO-level logging functions are provided that will report only the total function time if that total is
    below the time limit, and if above it will also log the sum of times for each call.

    Call times are recorded to a dictionary that is local to the decorated function. Keys are the name of calls, and the
    values are lists of execution times. This list is cleared after each execution. You can access this dictionary by
    providing alternative callbacks.

    Callback parameters include total execution time, time limit, the callable time dictionary, and a reference to the
    decorated function.

    Args:
        time_limit (float): Threshold that determines which callback run after decorated function runs.
        under_callback (Callable[[float, float, TimeDict, Callable[P, T]], None], optional): Called when execution time
            is under the time limit.
        over_callback (Callable[[float, float, TimeDict, Callable[P, T]], None], optional): Called when execution time
            is equal to or over the time limit.
    """
    _call_times: defaultdict[str, list[float]] = defaultdict(list)
    _call_names: dict[object, str] = {}

    def _get_name(call: Callable) -> str:
        """Use stored callable name or find if the callable is new."""
        try:
            return _call_names[call]
        except KeyError:
            pass

        _call_names[call] = _find_name(call)
        return _call_names[call]

    def _record_call_time(call: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Wrapper to record execution time of inner calls."""
        start = time.monotonic()
        try:
            return call(*args, **kwargs)
        finally:
            end = time.monotonic()
            _call_times[_get_name(call)].append(end - start)

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
                if duration < time_limit:
                    under_callback(duration, time_limit, _call_times.copy(), _new_func)
                else:
                    over_callback(duration, time_limit, _call_times.copy(), _new_func)
                _call_times.clear()
        return inner_wrapper
    return _measure_calls
