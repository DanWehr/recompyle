from recompyle import rewrite_wrap_calls


def basic_wrapper(call, *args, **kwargs):
    """Basic wrapper that prints before and after each call."""
    print(f"Before {call.__qualname__}, args: {args}, kwargs: {kwargs}")
    try:
        return call(*args, **kwargs)
    finally:
        print(f"After {call.__qualname__}")


def other_function(val: float) -> str:
    """Some other function being called."""
    return f"other val: {val}"


@rewrite_wrap_calls(wrap_call=basic_wrapper)
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for _ in (int(v) for v in range(count)):
        pass
    return other_function(val=123.45)


print(example_function(2))
