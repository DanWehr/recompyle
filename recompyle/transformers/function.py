"""Function transformers for ASTs."""
import ast
import itertools
import re

from recompyle.transformers.base import RecompyleBaseTransformer


class WrapCallsTransformer(RecompyleBaseTransformer):
    """Transforms a function AST by wrapping every call with the given call.

    This assumes that when the new function definition is executed, an object with the same name
    as wrap_call_name can be found in the execution locals or globals.
    """

    def __init__(
        self,
        wrap_call_name: str,
        blacklist: set[str] | None = None,
        whitelist: set[str] | None = None,
        initial_line: int = 0,
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

        super().__init__()
        self._wrap_call_name = wrap_call_name
        self.blacklist = blacklist
        self.whitelist = whitelist
        self._initial_line = initial_line

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
            case ast.Call(func=func):
                return f"{self._build_name(func)}"
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
            start, end, i = node.lineno, node.end_lineno, self._initial_line
            extras = {
                "ln_range": (start + i, end + i) if end is not None and end != start else (start + i,),
                "source": ast.unparse(node),
            }
            extras_tree = ast.parse(repr(extras)).body[0].value
            new_node = ast.Call(
                ast.Name(self._wrap_call_name, ast.Load()),
                args=[node.func, extras_tree, *node.args],
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

        # Temp remove decorators so they are not visited, then restore after visiting children
        decorator_cache = node.decorator_list
        node.decorator_list = []
        self.generic_visit(node)
        node.decorator_list = decorator_cache

        return node
