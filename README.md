# Recompyle

This package provides tools that can be used to rewrite and recompile source code, using the transformed version of the code at runtime. The initial proof-of-concept targets functions only, and only calls within them, but this project is structured to eventually expand to other forms of code rewriting.

Recompyle is written in pure Python using the standard library only, and has no additional dependencies.


# Installation

`pip install recompyle`


# Usage

The current implementation of Recompyle includes tools that wrap calls within a target function or method, allowing you to execute custom code before and/or after individual calls. The following example highlights a few different types of calls.

```python
def example_function():
    a = A()  # Calling a class to create an instance
    result = a.run(some_arg=5)  # Calling a method
    return int(result)  # Calling the 'int' builtin
```

Recompyle's call wrapping will apply to anything identified as an `ast.Call` when evaluating source code.


## Using the `wrap_calls` decorator

Unlike a typical decorator, `wrap_calls` does not actually wrap the decorated function. Instead it modifies the source of decorated function so that each call in its source (and that call's arguments) is passed through the given wrapper function (`basic_wrapper` in the example below).

The wrapper function must execute the call with those arguments, and return its return value, to ensure the behavior of the original decorated function is maintained.

```python
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from recompyle import wrap_calls

P = ParamSpec("P")
T = TypeVar("T")

def basic_wrapper(__call: Callable[P, T],  *args: P.args, **kwargs: P.kwargs) -> T:
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
```

This will produce the following output:

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

Only the `wrapper` parameter is required, and there are a number of optional parameters to control which calls will be wrapped. The full set of parameters includes:

- `wrapper` (Callable): Function or method that will wrap all calls inside target function.
- `ignore_builtins` (bool): Whether to skip wrapping builtin calls.
- `blacklist` (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use quotes, e.g. use a name of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an asterisk, like `"a[*]"` which would match all of `a[0]()` and `a[val]()` and `a["key"]()` etc.
- `whitelist` (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
- `rewrite_details` (dict | None): If provided the given dict will be updated to store the original function object and original/new source in the keys `original_func`, `original_source`, and `new_source`.

For further examples of `wrap_calls` see the tests in [test_rewrite_basic.py](tests/function/test_rewrite_basic.py). For examples of using the blacklist and whitelist, see [test_ignore_calls.py](tests/function/test_ignore_calls.py).


## Using the `flat_profile` decorator

This decorator uses call wrapping internally to record the execution times of all calls, in addition to the total execution time of the function. A time limit must be provided, and if the total time is below/above that limit then below/above callbacks will run.

The default callbacks will create a log message including the total time, and if the total is above the limit it will also include a summary of the times of all calls. If the total time exceeds the configured threshold, a log is created that includes the call execution times, ordered by longest calls first, making it easy to see which call caused the increase.

Multiple call times for the same name (e.g. from multiple `int()` calls) will be summed together for the default logging. Custom callbacks used instead of the default ones will receive the times of all individual calls.

```python
import logging
import time

from recompyle import flat_profile

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def slow_function(val: float) -> str:
    """Slow function being called."""
    time.sleep(0.5)  # Force total time of example_function over limit
    return f"other val: {val}"


def faster_function() -> None:
    """Faster function being called."""
    time.sleep(0.001)


@flat_profile(time_limit=0.3)
def example_function(count: int) -> str:
    """Function we are rewriting to time calls."""
    faster_function()
    for _ in (int(v) for v in range(count)):
        pass
    return slow_function(val=123.45)


log.info(example_function(2))
```

This will produce the following log output:

```text
INFO:recompyle.applied.flat_profiler:example_function finished in 0.506083s, above limit of 0.3s
('slow_function: 0.504s',
 'faster_function: 0.00175s',
 'int: 1.3e-06s',
 'range: 1.2e-06s')
INFO:__main__:other val: 123.45
```

Only the `time_limit` parameter is required. Several optional parameters are available to replace the default callbacks. The full set of parameters includes:

- `time_limit` (float): Threshold that determines which callback run after decorated function runs.
- `below_callback` (Callable | None): Called when execution time is under the time limit.
- `above_callback` (Callable | None): Called when execution time is equal to or over the time limit.
- `ignore_builtins` (bool): Whether to skip wrapping builtin calls.
- `blacklist` (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use quotes, e.g. use a name of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an asterisk, like `"a[*]"` which would match all of `a[0]()` and `a[val]()` and `a["key"]()` etc.
- `whitelist` (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
- `rewrite_details` (dict | None): If provided the given dict will be updated to store the original function object and original/new source in the keys `original_func`, `original_source`, and `new_source`.

A custom callback can be used in place of the default `below_callback` or `above_callback`. See [ProfilerCallback](recompyle/applied/flat_profiler.py) for details on the callback arguments.


## Custom Function Transformations

Wrapping calls is only one way source can be modified. Creating your own function/decorator that can modify source in new ways, beyond what Recompyle provides, will require the following steps:

1. Create at least one custom node transformer that extends [RecompyleBaseTransformer](recompyle/transformers/base.py). See [Green Tree Snakes](https://greentreesnakes.readthedocs.io/) for a great reference on working with ASTs. The transformers for the call wrapper can be found [here](recompyle/transformers/function.py) for reference.
2. Pass a target function and your transformer(s) to [rewrite_function()](recompyle/rewrite/rewrite_function.py). This will return a new function, modified and recompiled to include the transformations.
3. If the transformers support configuration, that can be handled by placing this process inside of another function. If the new function should replace the original, then this configuration is best done through a decorator.

# Performance

Performance has been measured using a [script](recompyle/performance.py) with multiple versions of a simple function with 10 calls, one of which is unmodified by Recompyle to serve as a reference for others that use the `wrap_calls` and `flat_profile` decorators. The numbers below are from running this script on an i7-6700K CPU, running Windows 10 with other software open at the same time.

```text
Running unwrapped function 100,000 times, repeat 100/100: average 0.7551001199990424 microseconds
Running simple wrapper 100,000 times, repeat 100/100: average 2.9637044099998096 microseconds
Running flat profiler w/ no callback 100,000 times, repeat 100/100: average 6.887421499999801 microseconds
Running flat profiler w/ default below callback 100,000 times, repeat 100/100: average 8.354579400000876 microseconds
Running flat profiler w/ default above callback 100,000 times, repeat 100/100: average 15.773746630000277 microseconds

Simple wrapper call cost is 0.2208604290000767 microseconds per wrapped call
Flat profiler call cost is 0.6132321380000759 microseconds per wrapped call
Flat profiler default below callback costs 1.4671579000010748 microseconds
Flat profiler default above callback costs 8.886325130000476 microseconds
```

The wrapper function used for testing `wrap_calls` does nothing outside of running the wrapped call, and so represents a bare minimum cost (~0.221 μs) that any further code in a wrapper would add onto. The flat profiler implements a call wrapper that records times before/after each call, and its ~0.613 μs addition to runtime cost includes the 0.221 minimum.

With these numbers if you applied the flat profiler to a function with 100 calls that are wrapped, used the default logging callbacks, and total function runtime was generally below the profiler time limit ("below" callback is triggered), then the flat profiler would add a total of only (100 * 0.613) + 1.467 = 62.767 μs to the execution time of the function. When the execution time is high enough to trigger the more costly "above" default callback (which processes and sorts call times to include them in its log message) this cost increases to 70.186 μs.

While this performance will differ across devices, with results of a small fraction of a millisecond this indicates the performance impact will typically be insignficant. This meets the original goal of being able to continuously monitor a function in a production system, especially if it is run infrequently such as once a second or less often.

To check performance on other devices, this script can be run with the command `python -m recompyle.performance`.

# Background

Recompyle came from wanting to monitor execution time of a function in a production system, and if an abnormal (above a threshold) execution time was encountered, to provide more detail than a simple decorator that just records the execution time of the entire function. Knowing *what* in the function was responsible for the time increase could help significantly with debugging/optimizing.

A full call stack would be the most useful which you can get through tools like the builtin cProfile, but there is typically enough overhead that it is not feasible for use in production. One way to address that overhead would be to only periodically profile the program (such as in statistical profiling), but that is primarily useful for monitoring your average execution behavior. If you want to watch for abnormal cases like a slowdown that happens rarely (say once a day), you need to be able to monitor the relevant code continuously, evaluating every execution to catch that rare event. For this to be possible, overhead must be very low.


## Flat Profiler

One way to handle the problem of profiling overhead would be to limit the scope of that profiling. Recompyle attempts to address this with a "flat profiler" (`recompyle.flat_profile`) that can capture the execution times of *all* calls within a decorated function, and *only* the calls within that function. It does not go deeper and profile the full call stack. Reduced overhead was a major goal for this work.

The flat profiler records the execution times of all callables in the decorated function or method, and if the total execution time is greater than a configurable time limit, the times of all internal calls will be logged in addition to the total.


## Recompiling Functions

Recompyle works by rewriting the source of the decorated function or method, at the time the module is loaded, to insert the wrapper and pass calls into it.

For example with the wrapped example function above:

```python
@wrap_calls(wrapper=basic_wrapper)
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

The original function is actually transformed into this alternate form by Recompyle, and the function object created from this new definition replaces the old one. This works through the following process:

1. The original function is compiled by python and passed into the decorator. Through the function object we can find the file the function came from, and what line its source starts on.
2. We read the original source and convert it into an Abstract Syntax Tree.
3. A series of transformers can be applied to the AST to modify the code.
4. After modification, the AST is compiled back into a *code* object and then executed, running the new function definition and creating a new callable function object.
5. The new function is returned by the decorator, replacing the original function.

Note also that in the rewritten version of the function above, the `wrap_calls` decorator is no longer present! If not removed, when we execute the new function definition in step 4 it would rerun the decorator and transform the function again, adding another layer of call wrapping and leading to an infinite recursion and exception on loading the module.


## Beyond Profiling

While this project started with a goal of creating the flat profiler, it quickly expanded to a larger goal. There are many packages that use ASTs to modify code, but typically this rewrite and recompile process is not very accessible and it can be difficult to understand how the process works. You're stuck with reading source code and building something yourself from scratch.

Recompyle attempts to make AST manipulation more accessible by providing a number of classes and functions that can either be reused directly in other projects, or at least serve as a clearer reference for your own custom code. The flat profiler itself is now implemented using a more generic call wrapper that can easily be used to execute any code before/after calls.

So far this package only provides tools for rewriting functions and wrapping calls within them, but it is intended for this to expand to include more transformers, and different targets beyond functions such as rewriting classes or modules as well. Suggestions are welcome!


# Current Limitations

- The rewrite+recompile process can only be applied to functions for which you have access to source code in a file that can be referenced. Applying it through decorators enforces this somewhat, but this also means it will not work on a function defined in the Python interpreter.
- The current implementation will lose access to nonlocal variables during the rewrite, so wrapping inner functions that use nonlocal variables is not yet supported.


# Contributing

Bugs, feedback and requests should all be handled through this project's [GitHub Issues](https://github.com/DanWehr/recompyle/issues) page.
