import warnings
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from recompyle.rewrite import CallWrapper, rewrite_wrap_calls_func

P = ParamSpec("P")
T = TypeVar("T")

WrapP = ParamSpec("WrapP")


def rewrite_wrap_calls(
    *,
    wrap_call: CallWrapper[WrapP],
    ignore_builtins: bool = False,
    blacklist: set[str] | None = None,
    whitelist: set[str] | None = None,
    rewrite_details: dict | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Deprecated, use `recompyle.wrap_calls` instead."""
    warnings.warn(
        "'rewrite_wrap_calls' has been renamed to 'wrap_calls' as of 0.2.0. The old name will be removed in 0.3.0.",
        category=DeprecationWarning,
        stacklevel=2,
    )

    def _call_wrapper(target_func: Callable[P, T]) -> Callable[P, T]:
        return rewrite_wrap_calls_func(
            target_func=target_func,
            wrapper=wrap_call,
            decorator_name="rewrite_wrap_calls",
            ignore_builtins=ignore_builtins,
            blacklist=blacklist,
            whitelist=whitelist,
            rewrite_details=rewrite_details,
        )

    return _call_wrapper


def wrap_calls(
    *,
    wrapper: CallWrapper[WrapP],
    ignore_builtins: bool = False,
    blacklist: set[str] | None = None,
    whitelist: set[str] | None = None,
    rewrite_details: dict | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Apply `rewrite.rewrite_function.rewrite_wrap_calls_func` to decorated function.

    Args:
        wrapper (CallWrapper): Function or method that will wrap all calls inside target function.
        ignore_builtins (bool): Whether to skip wrapping builtin calls.
        blacklist (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use
            quotes, e.g. use a name of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an
            asterisk, like `"a[*]"` which would match all of `a[0]()` and `a[val]()` and `a["key"]()` etc.
        whitelist (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
        rewrite_details (dict | None): If provided the given dict will be updated to store the original function object
            and original/new source in the keys `original_func`, `original_source`, and `new_source`.

    Returns:
        Callable: A decorator that will replace the wrapped function.
    """

    def _call_wrapper(target_func: Callable[P, T]) -> Callable[P, T]:
        return rewrite_wrap_calls_func(
            target_func=target_func,
            wrapper=wrapper,
            decorator_name="wrap_calls",
            ignore_builtins=ignore_builtins,
            blacklist=blacklist,
            whitelist=whitelist,
            rewrite_details=rewrite_details,
        )

    return _call_wrapper
