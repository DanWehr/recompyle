"""Definitions for rewriting and recompiling functions."""
import ast
import functools
import inspect
from collections.abc import Callable
from textwrap import dedent
from types import CodeType, FunctionType
from typing import ParamSpec, Protocol, TypeVar, cast

from recompyle.transformers import WrapCallsTransformer
from recompyle.transformers.base import RecompyleBaseTransformer

P = ParamSpec("P")
T = TypeVar("T")

WrapP = ParamSpec("WrapP")

WRAP_NAME = "_recompyle_wrap"


class CallWrapper(Protocol[P]):
    """Call wrapper protocol."""

    def __call__(self, __call: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Callable that can run extra code before/after a call.

        It must run the `__call` with the given args and kwargs, and return the call's return value:
            return __call(*args, **kwargs)
        """
        ...


class FunctionRewriter:
    """Stores and processes the target function.

    Attributes:
        target_func (FunctionType): The original function being processed.
    """

    def __init__(self, target_func: Callable):
        """Store and process the target function.

        Collects source information and generates the current AST representation.

        Args:
            target_func (FunctionType): Function to process.

        Raises:
            TypeError: If `func` is not a FunctionType, such as a class-based callable.
        """
        if not isinstance(target_func, FunctionType):
            raise TypeError("Only functions/methods supported for AST transformation.")
        self.target_func = target_func
        self._orig_source, self.filename, self.firstlineno = self._get_source()
        self._adjust_lineno = 0
        try:
            self._tree = ast.parse(source=self._orig_source, filename=self.filename, type_comments=True)
        except IndentationError:
            self._tree = ast.parse(source=dedent(self._orig_source), filename=self.filename, type_comments=True)

    def _get_source(self) -> tuple[str, str, int]:
        """Collect source and file data for function.

        Returns:
            tuple[str, str, int]: Function source, filename, and first line number.

        Raises:
            ValueError: If function is a builtin or source not available.
        """
        try:
            code = self.target_func.__code__
            filename = inspect.getsourcefile(code)
            if filename is None:
                raise ValueError("Source not available")
            source = inspect.getsource(code)
            firstlineno = code.co_firstlineno
        except TypeError as e:
            raise ValueError("Builtins not supported for uncompiling") from e
        except OSError as e:
            raise ValueError("Source not available") from e

        return source, filename, firstlineno

    def original_source(self) -> str:
        """Get the original source code of the target function, before any transformations.

        Returns:
            str: Original source code.
        """
        return self._orig_source

    def dump_tree(self, indent: int = 4) -> str:
        """Get a string representation of the current AST.

        Args:
            indent (int, optional): Indent size to use for nested AST elements, default 4.

        Returns:
            str: AST string.
        """
        return ast.dump(self._tree, indent=indent)

    def tree_to_source(self) -> str:
        """Get the current source code of the current AST, after any transformations.

        If no transformations have been applied through `transform_tree()` the returned
        source will be equivalent to the return of `original_source()`

        Returns:
            str: Current source code.
        """
        return ast.unparse(self._tree)

    def transform_tree(self, transformer: RecompyleBaseTransformer) -> None:
        """Transform the current tree with the given transformer.

        If the transformer adds or removes lines, a line number adjustment should also be given so that the resulting
        AST can have its line numbering corrected accordingly.

        Args:
            transformer (ast.NodeTransformer): The transformer to apply.
        """
        self._tree = transformer.visit(self._tree)
        # Adjust lineno for correct tracebacks, different depending on transform.
        self._adjust_lineno += transformer.adjust_lineno
        ast.increment_lineno(self._tree, self.firstlineno + self._adjust_lineno)
        ast.fix_missing_locations(self._tree.body[0])

    def compile_tree(self) -> CodeType:
        """Compile current AST back into function code object.

        Returns:
            CodeType: The compiled AST.

        Raises:
            TypeError: If the AST after transformations no longer represents a function definition.
        """
        if not isinstance(self._tree, ast.Module) or not isinstance(self._tree.body[0], ast.FunctionDef):
            raise TypeError("Only functions can be recompiled")
        return compile(source=self._tree, filename=self.filename, mode="exec", dont_inherit=True)


def rewrite_function(
    *,
    target_func: Callable[P, T],
    transformers: list[RecompyleBaseTransformer],
    custom_locals: dict[str, object] | None = None,
    rewrite_details: dict[str, object] | None = None,
) -> Callable[P, T]:
    """Generic rewriter for functions.

    Args:
        target_func (Callable): The function/method to rewrite.
        transformers (list[RecompyleBaseTransformer]): All transformers to appy in the order given.
        custom_locals (dict[str, object] | None): Optional locals dictionary to compile function with.
        rewrite_details (dict): If provided will be updated to store the original function object and original/new
            source in the keys `"original_func"`, `"original_source"`, and `"new_source"`.

    Returns:
        Callable: Rewritten function.
    """
    if hasattr(target_func, "__closure__") and target_func.__closure__:
        raise ValueError("Functions with non-local variables not supported for wrapping.")

    rewriter = FunctionRewriter(target_func)
    for transformer in transformers:
        rewriter.transform_tree(transformer)
    recompiled = rewriter.compile_tree()

    # Recompile into runnable function.
    f_name, f_globals = target_func.__name__, target_func.__globals__
    if custom_locals is None:
        custom_locals = {}
    exec(recompiled, f_globals, custom_locals)  # noqa: S102
    _new_func = cast(Callable[P, T], custom_locals[f_name])

    # Get actual function if this is a static or class method.
    nested = _new_func
    while hasattr(nested, "__wrapped__"):
        nested = nested.__wrapped__
    functools.update_wrapper(wrapper=nested, wrapped=target_func)  # Mainly to get qualname for methods.

    # Return details if dict was provided.
    if rewrite_details is not None:
        rewrite_details["original_func"] = target_func
        rewrite_details["original_source"] = rewriter.original_source()
        rewrite_details["new_source"] = rewriter.tree_to_source()

    return _new_func


def rewrite_wrap_calls_func(
    *,
    target_func: Callable[P, T],
    wrapper: CallWrapper[WrapP],
    decorator_name: str | None = None,
    ignore_builtins: bool = False,
    blacklist: set[str] | None = None,
    whitelist: set[str] | None = None,
    rewrite_details: dict[str, object] | None = None,
) -> Callable[P, T]:
    """Rewrites the target function so that every call is passed through the given `wrapper`.

    The `wrapper` must execute the call with its args and return the result of the call, much like a decorator. It
    will be passed into the rewritten target function through the keyword-only arg `_recompyle_wrap` which is added
    during the rewrite.

    If this is being used inside of a decorator, the name of that decorator must also be provided so that the decorator
    can be removed during the rewrite. Without this the decorator will be called again when recompiling the function,
    causing a crash due to infinite recursion.

    Args:
        target_func (Callable): The function/method to rewrite.
        wrapper (CallWrapper): The function to pass all calls through.
        decorator_name (str): The decorator name.
        ignore_builtins (bool): Whether to skip wrapping builtin calls.
        blacklist (set[str] | None): Call names that should not be wrapped. String literal subscripts should not use
            quotes, e.g. a pattern of `"a[b]"` to match code written as `a["b"]()`. Subscripts can be wildcards using an
            asterisk, like `"a[*]"` which would match code `a[0]()` and `a[1]()` and `a["key"]()` etc.
        whitelist (set[str] | None): Call names that should be wrapped. Allows wildcards like blacklist.
        rewrite_details (dict[str, object]): If provided will be updated to store the original function object and
            original/new source in the keys `"original_func"`, `"original_source"`, and `"new_source"`.

    Returns:
        Callable: Rewritten function with calls wrapped.
    """
    # Combine blacklist with builtins if needed.
    full_blacklist = blacklist
    if ignore_builtins:
        if full_blacklist is None:
            full_blacklist = set()
        builtin_calls = {key for key, value in target_func.__builtins__.items() if isinstance(value, Callable)}
        full_blacklist |= builtin_calls

    # Set up transformers and locals
    transformers: list[RecompyleBaseTransformer] = [
        WrapCallsTransformer(WRAP_NAME, decorator_name, blacklist=full_blacklist, whitelist=whitelist),
    ]
    custom_locals: dict[str, object] = {WRAP_NAME: wrapper}  # Provide ref for kwarg default through locals.

    return rewrite_function(
        target_func=target_func,
        transformers=transformers,
        custom_locals=custom_locals,
        rewrite_details=rewrite_details,
    )
