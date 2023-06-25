from collections.abc import Callable
from typing import Concatenate, ParamSpec, TypeVar

from recompyle.rewrite import rewrite_wrap_calls_func

P = ParamSpec("P")
T = TypeVar("T")

P2 = ParamSpec("P2")
T2 = TypeVar("T2")


def rewrite_wrap_calls(
    *, wrap_call: Callable[Concatenate[Callable[P2, T2], P2], T2],
    ignore_builtins: bool = False,
    rewrite_details: dict | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Apply `rewrite.rewrite_function.rewrite_wrap_calls_func`.

    Args:
        wrap_call (WrapCall): Callable that will wrap all calls inside target function.
        ignore_builtins (bool): Whether to skip wrapping builtin calls.
        rewrite_details (dict): If provided will be updated to store the original function object and original/new
            source in the keys `original_func`, `original_source`, and `new_source`.

    Returns:
        Callable: The decorator.
    """

    def _call_wrapper(target_func: Callable[P, T]) -> Callable[P, T]:
        return rewrite_wrap_calls_func(
            target_func=target_func,
            wrap_call=wrap_call,
            decorator_name="rewrite_wrap_calls",
            ignore_builtins=ignore_builtins,
            rewrite_details=rewrite_details,
        )
    return _call_wrapper
