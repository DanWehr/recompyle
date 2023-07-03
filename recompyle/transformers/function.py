"""Function transformers for ASTs."""
import ast


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

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Wrap every call node with `wrap_call`.

        Args:
            node (Call): Call definition to wrap.

        Returns:
            Call: Node after changes.
        """
        if self.ignore_names is None or node.func.id not in self.ignore_names:
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
