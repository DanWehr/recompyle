from collections.abc import Callable
from typing import ParamSpec, TypeVar

from recompyle import wrap_calls

P = ParamSpec("P")
T = TypeVar("T")


def basic_wrapper(__call: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Basic wrapper that prints before and after each call."""
    print(f"Before {__call.__qualname__}, args: {args}, kwargs: {kwargs}")
    try:
        return __call(*args, **kwargs)
    finally:
        print(f"After {__call.__qualname__}")


def other_function(val: float) -> str:
    """Some other function being called."""
    return f"other val: {val}"


@wrap_calls(wrapper=basic_wrapper)
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for _ in (int(v) for v in range(count)):
        pass
    return other_function(val=123.45)


print(example_function(2))
