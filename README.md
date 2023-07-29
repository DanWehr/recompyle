# Recompyle

This package provides tools that can be used to rewrite and recompile source code, using the transformed version of the code at runtime. The initial proof-of-concept targets functions only, but this project is structured to eventually expand to other forms of code rewriting.

Recompyle is written with pure Python using the standard library only, and has no additional dependencies.

## Installation

`pip install recompyle`


## Usage

The current implementation of Recompyle includes tools that allow for wrapping calls within a target function or method. The following example highlights a few different types of calls.

```python
def example_function():
    a = A()  # Calling a class
    result = a.run(some_arg=5)  # Calling a method
    return int(result)  # Calling the 'int' builtin
```

Recompyle's call wrapping will apply to anything identified as an `ast.Call` when evaluating source code. This could include calling a class, a function, or an object that implements `__call__`.


### Using the `rewrite_wrap_calls` decorator

This decorator is used to pass all callables through a simple function. You can think of the wrapper as being similar to a decorator, where you need to pass arguments to the wrapped function, and return its return value, so that the decorator does not interfere with the original use of the wrapped function.

Unlike a typical decorator, `rewrite_wrap_calls` does not wrap the decorated function, instead it wraps each called object within that function. It is still important to pass all arguments on to the inner object, and return its return value after it is executed. This ensures the decorated function still runs as was originally written.


```python
from recompyle import rewrite_wrap_calls

def basic_wrapper(call, *args, **kwargs):
    """Basic wrapper that prints before and after each call."""
    print(f"Before {call.__qualname__}")
    try:
        return call(*args, **kwargs)
    finally:
        print(f"After {call.__qualname__}")

def secondary_function():
    return "string from secondary function"

@rewrite_wrap_calls(wrap_call=basic_wrapper)
def example_function(count):
    for _ in (int(v) for v in range(count)):
        pass
    return secondary_function()

print(example_function(2))
```

Would produce the output:

```text
Before range
After range
Before int
After int
Before int
After int
Before secondary_function
After secondary_function
string from secondary function
```

Only the `wrap_call` parameter is required, but there are other optional parameters. The full set includes:

- `wrap_call` (Callable): Function or method that will wrap all calls inside target function.
- `ignore_builtins` (bool): Whether to skip wrapping builtin calls.
- `blacklist` (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use quotes, e.g. use a name of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an asterisk, like `"a[*]"` which would match all of `a[0]()` and `a[val]()` and `a["key"]()` etc.
- `whitelist` (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
- `rewrite_details` (dict | None): If provided the given dict will be updated to store the original function object and original/new source in the keys `original_func`, `original_source`, and `new_source`.


For further examples of `rewrite_wrap_calls` see the tests in `test_rewrite_basic.py`, and `test_ignore_calls.py` for examples of the blacklist and whitelist.

### Using the `shallow_call_profiler` decorator

This decorator is a more complex implementation of function rewriting. Rather than providing your own custom call wrapper, a wrapper defined internally is used to record the execution times of all calls, in addition to the execution time of the function overall. If the overall time exceeds the configured threshold, a log is created that includes the call execution times, making it easy to see which call caused the increase.

[Example goes here]

## Background

Recompyle came from wanting to monitor execution time of a function in a production system, and if an abnormal (above a threshold) execution time was encountered, to provide more detail than a simple decorator that just records the execution time of the entire function. Knowing *what* in the function was responsible for the time increase could help significantly with debugging/optimizing.

A full call stack would be the most useful through tools like the builtin `cProfile`, but there is typically enough overhead that it is not feasible for use in production. One way to address that overhead would be to only periodically profile the program (such as in statistical profiling), but that is primarily useful for improving your typical execution times. If you want to watch for abnormal cases like a slowdown that is rarely caused by an external resource, you need to be able to monitor the execution of the relevant code continuously, evaluating every execution. This would have to have a very low impact on processing time to be production safe.

### Shallow Profiler

One way to handle the problem of profiling overhead would be to limit the scope of that profiling. Recompyle attempts to address this with a "shallow profiler" (`recompyle.shallow_call_profiler`) that will capture the execution times of *all* calls within a decorated function, and *only* the calls within that function. It does not go deeper and profile the full call stack. Reduced overhead was the primary goal for this proof-of-concept.

The shallow profiler records the execution times of all callables in the decorated function or method, and if the total execution time is greater than a configurable time limit, the times of all internal calls will be logged in addition to the total.

### Recompiling Functions

Recompyle works by rewriting the source of the decorated function or method, at the time the module is loaded, to insert the wrapper and pass calls into it.

For example with the wrapped example function above:

```python
@rewrite_wrap_calls(wrap_call=basic_wrapper)
def example_function(count):
    for _ in (int(v) for v in range(count)):
        pass
    return secondary_function()
```

Would be roughly equivalent to:

```python
def example_function(count):
    for _ in (basic_wrapper(int, v) for v in basic_wrapper(range, count)):
        pass
    return basic_wrapper(secondary_function)
```

The original function is actually transformed into this alternate form by Recompyle, and the function object created from this new definition replaces the old one.

Note that for the transformed function, the `rewrite_wrap_calls` decorator is no longer present! If not removed, the rewrite process would repeat when recompiling this changed source back into a useable python object, and the rewrite would fail due to infinite recursion.


## Limitations

- The rewrite+recompile process can only be applied to functions for which you have access to source code in a file that can be referenced. Applying it through decorators enforces this somewhat, but this also means it will not work on a function defined in the Python interpreter.
- The current implementation will lose access to nonlocal variables during the rewrite, so wrapping inner functions that use nonlocal variables is not yet supported.
- By rewriting a function, it is possible to have code shown in the traceback of an exception no longer match the original source. This may be a solveable problem (see future enhancements).

## Future Enhancements

- Investigate optional support for modifying tracebacks to remove the callable wrapper (trace frame and text of source lines) such that the traceback matches original source again. If possible this should only be done if the error originates from original source. If an exception occurs in the wrapper, then the wrapper should of course still be part of the traceback.

## Development

[Not Yet Written]
