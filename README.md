# Recompyle

This package provides tools that can be used to rewrite and recompile source code, using the transformed version of the code at runtime. The initial proof-of-concept targets functions only, and only calls within them, but this project is structured to eventually expand to other forms of code rewriting.

Recompyle is written with pure Python using the standard library only, and has no additional dependencies.


# Installation

`pip install recompyle`


# Usage

The current implementation of Recompyle includes tools that allow for wrapping calls within a target function or method. The following example highlights a few different types of calls.

```python
def example_function():
    a = A()  # Calling a class to create an instance
    result = a.run(some_arg=5)  # Calling a method
    return int(result)  # Calling the 'int' builtin
```

Recompyle's call wrapping will apply to anything identified as an `ast.Call` when evaluating source code.


## Using the `rewrite_wrap_calls` decorator

This decorator is used to pass all callables and their parameters through a given wrapper function. You can think of the wrapper as being similar to a decorator, where you need to pass arguments to the wrapped function, and return its return value, so that the decorator does not interfere with the original use of the wrapped function.

Unlike a typical decorator, `rewrite_wrap_calls` does not actually wrap the decorated function. Instead it wraps each call in the source code of that function.

```python
from recompyle import rewrite_wrap_calls


def basic_wrapper(call, *args, **kwargs):
    """Basic wrapper that prints a line before and after each call."""
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
```

Would produce the print output:

```text
Before range, args: (2,), kwargs: {}
After range
Before int, args: (0,), kwargs: {}
After int
Before int, args: (1,), kwargs: {}
After int
Before other_function, args: (), kwargs: {'val': 123.45}
After other_function
other val: 123.45
```

Only the `wrap_call` parameter is required, but there are other optional parameters. The full set includes:

- `wrap_call` (Callable): Function or method that will wrap all calls inside target function.
- `ignore_builtins` (bool): Whether to skip wrapping builtin calls.
- `blacklist` (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use quotes, e.g. use a name of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an asterisk, like `"a[*]"` which would match all of `a[0]()` and `a[val]()` and `a["key"]()` etc.
- `whitelist` (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
- `rewrite_details` (dict | None): If provided the given dict will be updated to store the original function object and original/new source in the keys `original_func`, `original_source`, and `new_source`.

For further examples of `rewrite_wrap_calls` see the tests in [test_rewrite_basic.py](tests/function/test_rewrite_basic.py). For examples of using the blacklist and whitelist, see [test_ignore_calls.py](tests/function/test_ignore_calls.py).


## Using the `shallow_call_profiler` decorator

This decorator uses function rewriting internally to record the execution times of all calls, in addition to the total execution time of the function. A time limit must be provided, and if the total time is below/above that limit then a below/above callback will run.

The default callbacks will create a log showing the total time, and if the total is above the limit also log a summary of those calls. If the total time exceeds the configured threshold, a log is created that includes the call execution times, ordered by longest calls first, making it easy to see which call caused the increase. Multiple call times for the same name (e.g. from multiple `int()` calls) will be summed together into a single value for this default output.

```python
import logging
import time

from recompyle import shallow_call_profiler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def slow_function(val: float) -> str:
    """Slow function being called."""
    time.sleep(0.5)  # Force total time of example_function over limit
    return f"other val: {val}"


def faster_function() -> None:
    """Faster function being called."""
    time.sleep(0.001)


@shallow_call_profiler(time_limit=0.3)
def example_function(count: int) -> str:
    """Function we are rewriting to time calls."""
    faster_function()
    for _ in (int(v) for v in range(count)):
        pass
    return slow_function(val=123.45)


log.info(example_function(2))
```

Would produce the log output:

```text
INFO:recompyle.applied.shallow_profiler:example_function finished in 0.506083s, above limit of 0.3s
('slow_function: 0.504s',
 'faster_function: 0.00175s',
 'int: 1.3e-06s',
 'range: 1.2e-06s')
INFO:__main__:other val: 123.45
```

Only the `time_limit` parameter is required, but there are other optional parameters. The full set includes:

- `time_limit` (float): Threshold that determines which callback run after decorated function runs.
- `below_callback` (Callable | None): Called when execution time is under the time limit.
- `above_callback` (Callable | None): Called when execution time is equal to or over the time limit.

A custom callback used in place of the default `below_callback` or `above_callback`. See [ProfilerCallback](recompyle/applied/shallow_profiler.py) for details on the callback arguments.


## Custom Function Transformations

To create your own function/decorator that can modify function source code in new ways, you should only need to:

1. Create at least one custom node transformers that extends [RecompyleBaseTransformer](recompyle/transformers/base.py). See [Green Tree Snakes](https://greentreesnakes.readthedocs.io/) for a great reference on working with ASTs. The transformers for the call wrapper can be found [here](recompyle/transformers/function.py).
2. Pass a target function and your transformer(s) to [rewrite_function()](recompyle/rewrite/rewrite_function.py). This will return a new function, modified and recompiled to include the transformations.
3. If the transformers support configuration, that can be handled by placing this process inside of another function. If the new function should replace the original, this is best done with a decorator.


# Background

Recompyle came from wanting to monitor execution time of a function in a production system, and if an abnormal (above a threshold) execution time was encountered, to provide more detail than a simple decorator that just records the execution time of the entire function. Knowing *what* in the function was responsible for the time increase could help significantly with debugging/optimizing.

A full call stack would be the most useful which you can get through tools like the builtin cProfile, but there is typically enough overhead that it is not feasible for use in production. One way to address that overhead would be to only periodically profile the program (such as in statistical profiling), but that is primarily useful for monitoring your average execution behavior. If you want to watch for abnormal cases like a slowdown that is rarely (say once a day) caused by an external resource, you need to be able to monitor the relevant code continuously, evaluating every execution to catch that rare event. For this to be possible, overhead must be very low.


## Shallow Profiler

One way to handle the problem of profiling overhead would be to limit the scope of that profiling. Recompyle attempts to address this with a "shallow profiler" (`recompyle.shallow_call_profiler`) that will capture the execution times of *all* calls within a decorated function, and *only* the calls within that function. It does not go deeper and profile the full call stack. Reduced overhead was a major goal for this work.

The shallow profiler records the execution times of all callables in the decorated function or method, and if the total execution time is greater than a configurable time limit, the times of all internal calls will be logged in addition to the total.


## Recompiling Functions

Recompyle works by rewriting the source of the decorated function or method, at the time the module is loaded, to insert the wrapper and pass calls into it.

For example with the wrapped example function above:

```python
@rewrite_wrap_calls(wrap_call=basic_wrapper)
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for _ in (int(v) for v in range(count)):
        pass
    return other_function(val=123.45)
```

Would be roughly equivalent to:

```python
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for _ in (basic_wrapper(int, v) for v in basic_wrapper(range, count)):
        pass
    return basic_wrapper(other_function, val=123.45)
```

The original function is actually transformed into this alternate form by Recompyle, and the function object created from this new definition replaces the old one. This works roughly through the following process:

1. The original function is compiled by python and passed into the decorator. Through this we can find the file the function came from, and what line its source starts on.
2. We read the original source and transform it into an Abstract Syntax Tree.
3. A series of transformers can be applied to the AST to modify the code.
4. After modification, the AST is compiled back into a *code* object and then executed, running the new function definition and creating a new callable function object.
5. The new function is returned by the decorator, replacing the original function.

Note also that in the rewritten version of the function, the `rewrite_wrap_calls` decorator is no longer present! If not removed, when we execute the new function definition above in step 4 it would rerun the decorator as well, leading to an infinite recursion and exception on loading the module.


## Beyond Profiling

While this project started with a goal of creating the shallow call profiler, it quickly expanded to a larger goal. There are many packages that use ASTs to modify code, but typically this rewrite and recompile process is not very accessible and it can be difficult to understand how the process works. You're stuck with reading source code and building something yourself from scratch.

Recompyle attempts to make AST manipulation more accessible by providing a number of classes and functions that can either be reused directly in other projects, or at least serve as a clearer reference for your own custom code. The shallow profiler itself is now implemented using a more generic call wrapper that can easily be used to execute any code before/after calls.

While this package only provides tools for rewriting functions and wrapping calls within them, it is intended for this to expand to include more transformers transformers, and different targets beyond functions such as rewriting classes or modules as well.


# Limitations

- The rewrite+recompile process can only be applied to functions for which you have access to source code in a file that can be referenced. Applying it through decorators enforces this somewhat, but this also means it will not work on a function defined in the Python interpreter.
- The current implementation will lose access to nonlocal variables during the rewrite, so wrapping inner functions that use nonlocal variables is not yet supported.
- By rewriting a function, it is possible to have code shown in the traceback of an exception no longer match the original source. This may be a solveable problem (see future enhancements).

# Future Enhancements

- Investigate optional support for modifying tracebacks to remove the call wrapper (trace frame and text of source lines) such that the traceback matches original source again. If possible this should only be done if the error originates from original source. If an exception occurs in the wrapper, then the wrapper should of course still be part of the traceback.

# Contributing

Bugs, feedback and requests should all be handled through this project's [GitHub Issues](https://github.com/DanWehr/recompyle/issues) page.
