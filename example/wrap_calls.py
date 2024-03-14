from collections.abc import Callable
from typing import ParamSpec, TypeVar

from recompyle import wrap_calls

P = ParamSpec("P")
T = TypeVar("T")


def basic_wrapper(__call: Callable[P, T], _, *args: P.args, **kwargs: P.kwargs) -> T:
    """Basic wrapper that prints before and after each call."""
    print(f"Before {__call.__qualname__}, args: {args}, kwargs: {kwargs}")
    try:
        return __call(*args, **kwargs)
    finally:
        print(f"After {__call.__qualname__}")


def other_function(val: float) -> str:
    """Some other function being called."""
    return str(val)


@wrap_calls(wrapper=basic_wrapper)
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for v in range(count):
        int(v)
    return other_function(val=123.45)


print("Before calling wrapped function")
print("Printing function return:", example_function(2))
print("After calling wrapped function")
