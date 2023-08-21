"""Function transformers for ASTs."""
import ast
import itertools
import re

from recompyle.transformers.base import RecompyleBaseTransformer


class RemoveDecoratorTransformer(RecompyleBaseTransformer):
    """Transforms a function AST by optionally removing a decorator."""

    def __init__(self, remove_decorator: str | None = None):
        """NodeTransformer that can optionally remove a decorator from a FunctionDef.

        Args:
            remove_decorator (str | None): Name of the decorator to remove.
        """
        super().__init__()
        self._dec_name = remove_decorator

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Remove decorator if provided to prevent recursion on recompile.

        Args:
            node (FunctionDef): Description

        Returns:
            FunctionDef: Node after potential decorator removal.

        Raises:
            ValueError: If decorator to remove is not found.
        """
        # Remove decorator if provided to prevent recursion on compile.
        if self._dec_name is not None:
            new_deco_list = [val for val in node.decorator_list if not self._is_deco_target(val)]
            if len(new_deco_list) == len(node.decorator_list):
                err_str = f"Decorator named '{self._dec_name}' not found."
                raise ValueError(err_str)
            node.decorator_list = new_deco_list
            self.adjust_lineno -= 1

        self.generic_visit(node)
        return node

    def _is_deco_target(self, node: ast.expr) -> bool:
        """Check if the decorator node is the target decorator.

        Args:
            node (ast.expr): Description

        Returns:
            bool: Description

        Raises:
            TypeError: If the decorator is an unexpected node type.
        """
        match node:
            case ast.Name(id=name):
                # Decorator
                return name == self._dec_name
            case ast.Call(func=ast.Name(id=name)):
                # Decorator factory
                return name == self._dec_name
            case _:
                err_str = f"Decorator type {node.__class__.__name__} not supported."
                raise TypeError(err_str)


class WrapCallsTransformer(RemoveDecoratorTransformer):
    """Transforms a function AST by wrapping every call with the given call.

    This assumes that when the new function definition is executed, an object with the same name
    as wrap_call_name can be found in the execution locals or globals.
    """

    def __init__(
        self,
        wrap_call_name: str,
        remove_decorator: str | None = None,
        blacklist: set[str] | None = None,
        whitelist: set[str] | None = None,
    ):
        """Store `wrap_call` for wrapping calls.

        Args:
            wrap_call_name (str): Callable to wrap all calls with.
            remove_decorator (str | None): Name of the decorator to remove.
            blacklist (set[str] | None): Optional call names that should not be wrapped.
            whitelist (set[str] | None): Optional call names that should be wrapped.
        """
        if blacklist and whitelist:
            raise ValueError("Call blacklist and whitelist can not both be used at once")

        super().__init__(remove_decorator=remove_decorator)
        self._wrap_call_name = wrap_call_name
        self.blacklist = blacklist
        self.whitelist = whitelist

    def _build_name(self, node: ast.expr) -> str:
        """Recursively builds a call name from an AST.

        String literals are returned without quotes to reduce the complexity of the match. This allows us to skip the
        handling combinations of single or double quotes which are equivalent. For example `obj["x"]["y"]["z"]()` could
        be matched by both `obj['x']["y"]['z']` and `obj["x"]['y']["z"]` patterns if we included quotes. This can be
        revisited if there is enough need to differentiate between `obj['a']` and `obj[a]`.

        Args:
            node (expr): Node to build name from.

        Returns:
            str: Full call name.

        Raises:
            TypeError: If a node function type other than Name or Attribute is encountered.
        """
        match node:
            case ast.Constant(value=name):
                return str(name)
            case ast.Name(id=name):
                return name
            case ast.Attribute(value=next_node, attr=name):
                return f"{self._build_name(next_node)}.{name}"
            case ast.Subscript(value=next_node, slice=inner):
                return f"{self._build_name(next_node)}[{self._build_name(inner)}]"
            case _:
                raise TypeError(f"Unknown call node type: {type(node)}")

    def _allow_name(self, name: str) -> bool | None:
        """Check name against blacklist and whitelist.

        Args:
            name (str): The name to check.

        Returns:
            bool | None: Bool if the name should be allowed or rejected, None to allow more checks.
        """
        if self.blacklist and name in self.blacklist:
            return False
        if self.whitelist and name in self.whitelist:
            return True
        return None

    def _allow_wrap_call(self, node: ast.Call) -> bool:
        """Determine if call node should be wrapped.

        Args:
            node (Call): Node to check.

        Returns:
            bool: True if call should be wrapped, False otherwise.
        """
        # Do not wrap globals() or locals(), different results if run in wrapper
        match node:
            case ast.Call(func=ast.Name(id=check)):
                if check in ("globals", "locals"):
                    return False

        # Default allow if not filtering.
        if not self.blacklist and not self.whitelist:
            return True

        # We must have a non-empty blacklist or whitelist, try exact match first.
        full_name = self._build_name(node.func)
        if (result := self._allow_name(full_name)) is not None:
            return result

        # Create alternative names that could match with wildcards.
        matches = list(re.finditer(r"\[(.*?)\]", full_name))
        for i in range(1, len(matches) + 1):
            for c in itertools.combinations(matches, i):
                wildcard_name = full_name
                # Replace combinations in reverse order as string length may change.
                for m in reversed(c):
                    wildcard_name = wildcard_name[: m.start()] + "[*]" + wildcard_name[m.end() :]
                if (result := self._allow_name(wildcard_name)) is not None:
                    return result

        # If using blacklist default is allow if not found, otherwise block as we must be using whitelist.
        return bool(self.blacklist)

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Wrap every call node that is not ignored with `wrap_call`.

        Args:
            node (Call): Call definition to wrap.

        Returns:
            Call: Node after changes.
        """
        if self._allow_wrap_call(node):
            new_node = ast.Call(
                ast.Name(self._wrap_call_name, ast.Load()),
                args=[node.func, *node.args],
                keywords=node.keywords,
            )
            ast.copy_location(new_node, node)
        else:
            new_node = node

        self.generic_visit(new_node)
        return new_node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Add wrap_func as last keyword param.

        Args:
            node (FunctionDef): Function definition node to modify.

        Returns:
            ast.FunctionDef: Node after changes.
        """
        # Add measure func as last param.
        node.args.kwonlyargs.append(ast.arg(self._wrap_call_name))
        node.args.kw_defaults.append(ast.Name(id=self._wrap_call_name, ctx=ast.Load()))

        return super().visit_FunctionDef(node)
