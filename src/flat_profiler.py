from collections import defaultdict
from pprint import pformat
import time
from _src_rewrite import _rewrite_function
import functools
from operator import itemgetter


def flat_call_profiler(func=None, *, time_limit=1):
    _functimes = defaultdict(list)

    def _print_sorted_times():
        sum_times = ((func_str, sum(times)) for func_str, times in _functimes.items())
        sum_times = (f"{func_str}: {time:.3f}s" for func_str, time in sorted(sum_times, key=itemgetter(1), reverse=True))
        print("Logged Times:", pformat(tuple(sum_times)), sep="\n")

    def _record_call_time(func, *args, **kwargs):
        # Record execution time of the inner call.
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
        except Exception:
            raise
        finally:
            end = time.monotonic()
            _functimes[func.__qualname__].append(end - start)
        return result

    def _measure_calls(func):
        # Use other decorator to reprogram function here.
        _new_func = _rewrite_function(func=func, wrap_func=_record_call_time, decorator_name="flat_call_profiler")

        @functools.wraps(func)
        def inner_wrapper(*args, **kwargs):
            _functimes.clear()
            start = time.monotonic()
            try:
                result = _new_func(*args, **kwargs)
            finally:
                duration = time.monotonic() - start
                if duration < time_limit:
                    print(f"{func.__qualname__} took {duration:.3f}s to run, below the {time_limit}s limit.")
                else:
                    print(f"{func.__qualname__} took {duration:.3f}s to run, above the {time_limit}s limit.")
                    _print_sorted_times()
            return result
        # print(f"----- Completed Wrap of {func.__qualname__}")
        return inner_wrapper

    if func:
        return _measure_calls(func)
    return _measure_calls
