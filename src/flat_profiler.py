from collections import defaultdict
from pprint import pformat
import time
from _src_rewrite import FunctionRewriter, WrapCallsDecoratorTransformer
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
        # Reprogram function, adjust lines because we remove the decorator.
        func_ast = FunctionRewriter(func)
        # print(f"----- Starting Wrap of {func.__qualname__}")
        # print(func_ast.original_source())
        # print(func_ast.dump_tree())
        # Transform and adjust lines to handle removing decorator.
        func_ast.transform_tree(WrapCallsDecoratorTransformer("_record_call_time", "flat_call_profiler"), -1)
        # print(func_ast.tree_to_source())
        recompiled = func_ast.compile_tree()
        exec(recompiled)
        _new_func = locals()[func.__name__]
        # Prefill the measurement callbac.
        _new_func = functools.partial(_new_func, _record_call_time=_record_call_time)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
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
        return wrapper

    if func:
        return _measure_calls(func)
    return _measure_calls
