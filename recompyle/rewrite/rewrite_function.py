"""Definitions for rewriting and recompiling functions."""
import ast
import functools
import inspect
from collections.abc import Callable
from textwrap import dedent
from types import CodeType, FunctionType
from typing import Concatenate, ParamSpec, TypeVar, cast

from recompyle.transformers import WrapCallsTransformer

P = ParamSpec("P")
T = TypeVar("T")

P2 = ParamSpec("P2")
T2 = TypeVar("T2")

WRAP_NAME = "_recompyle_wrap"


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
            RuntimeError: If `func` is not a FunctionType, such as a class-based callable.
        """
        if not isinstance(target_func, FunctionType):
            raise RuntimeError("Only functions supported for AST transformation.")
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
            RuntimeError: If function is a builtin or source not available.
        """
        try:
            code = self.target_func.__code__
            filename = inspect.getsourcefile(code)
            if filename is None:
                raise RuntimeError("Source not available")
            source = inspect.getsource(code)
            firstlineno = code.co_firstlineno
        except TypeError as e:
            raise RuntimeError("Builtins not supported for uncompiling") from e
        except OSError as e:
            raise RuntimeError("Source not available") from e

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

    def transform_tree(self, transformer: ast.NodeTransformer, adjust_lineno: int = 0) -> None:
        """Transform the current tree with the given transformer.

        If the transformer adds or removes lines, a line number adjustment should also be given
        so that the resulting AST can have its line numbering corrected accordingly.

        Args:
            transformer (ast.NodeTransformer): The transformer to apply.
            adjust_lineno (int, optional): The line number adjustment.
        """
        self._tree = transformer.visit(self._tree)
        # Adjust lineno for correct tracebacks, different depending on transform.
        self._adjust_lineno += adjust_lineno
        ast.increment_lineno(self._tree, self.firstlineno + self._adjust_lineno)
        ast.fix_missing_locations(self._tree.body[0])

    def compile_tree(self) -> CodeType:
        """Compile current AST back into function code object.

        Returns:
            CodeType: The compiled AST.

        Raises:
            RuntimeError: If the AST after transformations no longer represents a function definition.
        """
        if not isinstance(self._tree, ast.Module) or not isinstance(self._tree.body[0], ast.FunctionDef):
            raise RuntimeError("Only functions can be recompiled")
        return compile(source=self._tree, filename=self.filename, mode="exec")


def rewrite_wrap_calls_func(
    *,
    target_func: Callable[P, T],
    wrap_call: Callable[Concatenate[Callable[P2, T2], P2], T2],
    decorator_name: str | None = None,
    ignore_builtins: bool = False,
    rewrite_details: dict | None = None,
) -> Callable[P, T]:
    """Rewrites the target function so that every call is passed through the given `wrap_call`.

    The `wrap_call` must execute the call with its args and return the result of the call, much like a decorator. It
    will be passed into the rewritten target function through the keyword-only arg `_recompyle_wrap` which is added
    during the rewrite.

    If this is being used inside of a decorator, the name of that decorator must also be provided so that the decorator
    can be removed during the rewrite. Without this the decorator will be called again when recompiling the function,
    causing a crash due to infinite recursion.

    Args:
        target_func (FunctionType): The function/method to rewrite.
        wrap_call (Callable): The function to pass all calls through.
        decorator_name (str): The decorator name.
        ignore_builtins (bool): Whether to skip wrapping builtin calls.
        rewrite_details (dict): If provided will be updated to store the original function object and original/new
            source in the keys `original_func`, `original_source`, and `new_source`.
    """
    if not isinstance(target_func, FunctionType):
        RuntimeError("Only functions/methods supported for rewrite")

    # Reprogram function, adjust lines because we remove the decorator.
    rewriter = FunctionRewriter(target_func)

    # Transform and adjust lines to handle removing decorator.
    ignore_names = target_func.__builtins__.keys() if ignore_builtins else None
    transformer = WrapCallsTransformer(WRAP_NAME, decorator_name, ignore_names=ignore_names)
    rewriter.transform_tree(transformer, transformer.adjust_lineno)
    recompiled = rewriter.compile_tree()

    if rewrite_details is not None:
        rewrite_details["original_func"] = target_func
        rewrite_details["original_source"] = rewriter.original_source()
        rewrite_details["new_source"] = rewriter.tree_to_source()

    restore_ref = None
    name_existed = None
    f_name, f_globals = target_func.__name__, target_func.__globals__
    if (name_existed := f_name in f_globals) and f_globals[f_name] is not target_func:
        # We found a different globals object that shares a name with what we're wrapping.
        restore_ref = f_globals[f_name]

    # Create runnable function.
    exec(recompiled, f_globals)  # noqa: S102
    _new_func = cast(Callable[P, T], f_globals[f_name])
    nested = _new_func
    while hasattr(nested, "__wrapped__"):
        nested = nested.__wrapped__
    functools.update_wrapper(wrapper=nested, wrapped=target_func)  # Mainly to get qualname for methods.
    # Replace the None default with our call wrapper. Cleaner than using functools.[partial|partialmethod].
    nested.__kwdefaults__[WRAP_NAME] = wrap_call

    if name_existed is False:
        # Global name was empty, clear it again.
        del f_globals[f_name]
    elif restore_ref is not None:
        # Put the other global object back.
        f_globals[f_name] = restore_ref

    return _new_func
