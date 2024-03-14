# Recompyle

This package provides tools that can be used to rewrite and recompile source code, using the transformed version of the code at runtime. The initial proof-of-concept targets functions only, with an example transformer to wrap calls within those functions. Over time more transformers will be added, as well as more targets than just functions.

Recompyle is written in pure Python using the standard library only, and has no additional dependencies.


# Installation

`pip install recompyle`


# Usage

Recompyle's first transformer allows you to wrap calls within a target function or method, allowing you to execute custom code before and/or after individual calls. The following example highlights a few different types of calls.

```python
def example_function():
    a = A()  # Calling a class to create an instance
    result = a.run(some_arg=5)  # Calling a method
    return int(result)  # Calling the 'int' builtin
```

Call wrapping will apply to anything identified as an `ast.Call` when converting source code to an Abstract Syntax Tree.


## Using the `wrap_calls` decorator

Unlike a typical decorator, `wrap_calls` does not actually wrap the decorated function. Instead it modifies the source of decorated function so that each call in its source (and that call's arguments) is passed through the given wrapper function (`basic_wrapper` in the example below).

The wrapper function must execute the call with those arguments, and return its return value, to ensure the behavior of the original decorated function is maintained.

```python
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
```

This will produce the following output:

```text
Before calling wrapped function
Before range, args: (2,), kwargs: {}
After range
Before int, args: (0,), kwargs: {}
After int
Before int, args: (1,), kwargs: {}
After int
Before other_function, args: (), kwargs: {'val': 123.45}
After other_function
Printing function return: 123.45
After calling wrapped function
```

For full information on the signature required for the wrapper, see the [CallWrapper protocol](recompyle/rewrite/rewrite_function.py).

Only the `wrapper` parameter of the `wrap_calls` decorator is required, and there are a number of optional parameters to control which calls will be wrapped. The full set of parameters includes:

- `wrapper` (Callable): Function or method that will wrap all calls inside target function.
- `ignore_builtins` (bool): Whether to skip wrapping builtin calls.
- `blacklist` (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use quotes, e.g. use a name of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an asterisk, like `"a[*]"` which would match all of `a[0]()` and `a[val]()` and `a["key"]()` etc.
- `whitelist` (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
- `rewrite_details` (dict | None): If provided the given dict will be updated to store the original function object and original/new source in the keys `original_func`, `original_source`, and `new_source`.

For further examples of `wrap_calls` see the tests in [test_rewrite_basic.py](tests/function/test_rewrite_basic.py). For examples of using the blacklist and whitelist, see [test_ignore_calls.py](tests/function/test_ignore_calls.py).


## Custom Function Transformers

Wrapping calls is only one way source can be modified. Creating your own function/decorator that can modify source in new ways, beyond what Recompyle provides, will require the following steps:

1. Create at least one custom node transformer that extends [RecompyleBaseTransformer](recompyle/transformers/base.py). See [Green Tree Snakes](https://greentreesnakes.readthedocs.io/) for a great reference on working with ASTs. The transformers for the call wrapper can be found [here](recompyle/transformers/function.py) for reference.
2. Pass a target function and your transformer(s) to [rewrite_function()](recompyle/rewrite/rewrite_function.py). This will return a new function, modified and recompiled to include the transformations.
3. If the new transformer support configuration, this is best handled through a parametrized decorator that internally executes the above steps.


# How `wrap_calls` Works

The `wrap_calls` decorator works by rewriting the source of the decorated function or method, at the time the module is loaded, to insert the wrapper and pass calls into it.

For example the wrapped example function above:

```python
@wrap_calls(wrapper=basic_wrapper)
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for v in range(count):
        int(v)
    return other_function(val=123.45)
```

Would be roughly equivalent to:

```python
@wrap_calls(wrapper=basic_wrapper)
def example_function(count: int) -> str:
    """Function we are rewriting to wrap calls."""
    for v in basic_wrapper(range, ..., count):
        basic_wrapper(int, ..., v)
    return basic_wrapper(other_function, ..., val=123.45)
```

The original function is actually transformed into this alternate form by Recompyle, and the function object created from this new definition replaces the old one. For brevity the second argument to the wrapper has been replaced by `...` in this example. In practice this second argument will be a dictionary that includes line and source info on the call for easy reference in the wrapper.

This works through the following process:

1. The original function is compiled by python and passed into the `wrap_calls` decorator. Through this function object we can find the file the function came from, and what line its source starts on.
2. We read the original source and convert it into an Abstract Syntax Tree.
3. Transformers are applied to the AST to modify the code.
4. After modification, the AST is compiled back into a Python *code* object and then executed, running the new function definition and creating a new callable function object.
5. The new function is returned by the decorator, replacing the original function.


## Future Additions

This project started from a goal of creating a flat profiler (see the [flat_profiler](https://github.com/DanWehr/flat_profiler) project), but Recompyle now exists separately to support a larger goal. There are many packages that use ASTs to modify code, but typically this rewrite and recompile process is not very accessible and it can be difficult to understand how the process works. If you want to do this, you're stuck with building something yourself from scratch.

Recompyle attempts to make AST manipulation more accessible by providing a number of classes and functions that can either be reused directly in other projects, or at least serve as a clearer reference for your own custom code.

So far this package only provides tools for rewriting functions and wrapping calls within them, but it is intended for this to expand to include more transformers, and different targets beyond functions such as rewriting classes or modules as well. Suggestions are welcome!


# Current Limitations

- The rewrite+recompile process can only be applied to functions for which you have access to source code in a file that can be referenced. Applying it through decorators enforces this somewhat, but this also means it will not work on a function defined in the Python interpreter.
- The current implementation will lose access to nonlocal variables during the rewrite, so wrapping inner functions that use nonlocal variables is not yet supported.


# Contributing

Bugs, feedback and requests should all be handled through this project's [GitHub Issues](https://github.com/DanWehr/recompyle/issues) page.
