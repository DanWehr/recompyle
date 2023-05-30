from typing import Callable
from _src_rewrite import _rewrite_function
import functools


class WrapperFuncNameUsed(Exception):
    pass


def call_wrapper(*, wrap_func: Callable, wrap_func_name: str = "_wrap_func"):
    def _call_wrapper(func):
        _new_func = _rewrite_function(func=func, wrap_func=wrap_func, decorator_name="call_wrapper")

        @functools.wraps(func)
        def inner_wrapper(*args, **kwargs):
            # TODO Hide wrap_func_name from stack trace if it isn't the source of the issue.
            return _new_func(*args, **kwargs)
        return inner_wrapper
    return _call_wrapper
