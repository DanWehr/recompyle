"""Function transformers for ASTs."""
import ast
import itertools
import re


class RemoveDecoratorTransformer(ast.NodeTransformer):
    """Transforms a function AST by optionally removing a decorator."""

    def __init__(self, remove_decorator: str | None = None):
        """NodeTransformer that can optionally remove a decorator from a FunctionDef.

        Args:
            remove_decorator (str | None): Name of the decorator to remove.
        """
        super().__init__()
        self._dec_name = remove_decorator
        self.adjust_lineno = -1 if remove_decorator is not None else 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Remove decorator if provided to prevent recursion on recompile.

        Args:
            node (FunctionDef): Description

        Returns:
            FunctionDef: Node after potential decorator removal.

        Raises:
            RuntimeError: Description
        """
        # Remove decorator if provided to prevent recursion on compile.
        if self._dec_name is not None:
            new_deco_list = [val for val in node.decorator_list if not self._is_deco_target(val)]
            if len(new_deco_list) == len(node.decorator_list):
                err_str = f"Decorator named '{self._dec_name}' not found."
                raise RuntimeError(err_str)
            node.decorator_list = new_deco_list
            self.adjust_lineno = -1

        self.generic_visit(node)
        return node

    def _is_deco_target(self, node: ast.expr) -> bool:
        """Check if the decorator node is the target decorator.

        Args:
            node (ast.expr): Description

        Returns:
            bool: Description

        Raises:
            RuntimeError: If the decorator is an unexpected node type.
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
                raise RuntimeError(err_str)


class WrapCallsTransformer(RemoveDecoratorTransformer):
    """Transforms a function AST by wrapping every call with the given call.

    This assumes that when the new function definition is executed, an object with the same name
    as wrap_call_name can be found in the execution locals or globals.
    """

    def __init__(
        self, wrap_call_name: str, remove_decorator: str | None = None, ignore_names: set[str] | None = None,
    ):
        """Store `wrap_call` for wrapping calls.

        Args:
            wrap_call_name (str): Callable to wrap all calls with.
            remove_decorator (str | None): Name of the decorator to remove.
            ignore_names (set[str] | None): Optional call names that should not be wrapped.
        """
        super().__init__(remove_decorator=remove_decorator)
        self._wrap_call_name = wrap_call_name
        self.ignore_names = ignore_names

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
            RuntimeError: If a node function type other than Name or Attribute is encountered.
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
                raise RuntimeError(f"Unknown call node type: {type(node)}")

    def _allow_wrap_call(self, node: ast.Call) -> bool:
        """Determine if call node should be wrapped.

        Args:
            node (Call): Node to check.

        Returns:
            bool: True if call should be wrapped, False otherwise.
        """
        if self.ignore_names is None:
            return True

        full_name = self._build_name(node.func)
        if full_name in self.ignore_names:
            return False

        # Create alternative names that could match with wildcards.
        matches = list(re.finditer(r'\[(.*?)\]', full_name))
        if matches:
            wildcard_names = []
            for i in range(1, len(matches) + 1):
                for c in itertools.combinations(matches, i):
                    # Replace combinations in reverse order as string length may change.
                    n = full_name
                    for m in reversed(c):
                        n = n[:m.start()] + "[*]" + n[m.end():]
                    wildcard_names.append(n)
            for wildcard_name in wildcard_names:
                if wildcard_name in self.ignore_names:
                    return False
        return True

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Wrap every call node that is not ignored with `wrap_call`.

        Args:
            node (Call): Call definition to wrap.

        Returns:
            Call: Node after changes.
        """
        if self._allow_wrap_call(node):
            new_node = ast.Call(
                ast.Name(self._wrap_call_name, ast.Load()), args=[node.func, *node.args], keywords=node.keywords,
            )
            ast.copy_location(new_node, node)
        else:
            new_node = node

        self.generic_visit(node)
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
