import ast
import inspect
from types import FunctionType
from textwrap import dedent


class FunctionRewriter():
    def __init__(self, func: FunctionType):
        if not isinstance(func, FunctionType):
            raise RuntimeError("Only functions supported for AST transformation.")
        self.func = func
        self._orig_source, self.filename, self.firstlineno = self._get_source()
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
            code = self.func.__code__
            filename = inspect.getsourcefile(code)
            if filename is None:
                raise RuntimeError("Source not available")
            source = inspect.getsource(code)
            firstlineno = code.co_firstlineno
        except TypeError:
            raise RuntimeError("Builtins not supported for uncompiling")
        except OSError:
            raise RuntimeError("Source not available")

        return source, filename, firstlineno

    def original_source(self) -> str:
        return self._orig_source

    def dump_tree(self, indent=4):
        return ast.dump(self._tree, indent=indent)

    def tree_to_source(self) -> str:
        return ast.unparse(self._tree)

    def transform_tree(self, transformer: ast.NodeTransformer, adjust_lineno=0):
        """Replace current AST with transformer results."""
        self._tree = transformer.visit(self._tree)
        # Adjust lineno for correct tracebacks, different depending on how
        ast.increment_lineno(self._tree, self.firstlineno + adjust_lineno)
        ast.fix_missing_locations(self._tree.body[0])

    def compile_tree(self):
        """Compile current AST back into function code object."""
        if not isinstance(self._tree, ast.Module) or not isinstance(self._tree.body[0], ast.FunctionDef):
            raise RuntimeError("Only functions can be recompiled")
        return compile(self._tree, self.filename, "exec")


class WrapCallsDecoratorTransformer(ast.NodeTransformer):
    def __init__(self, wrap_func, remove_decorator=None):
        self._wrap_func = wrap_func
        self._dec_name = remove_decorator
        super().__init__()

    def visit_Call(self, node):
        """Wrap every call with the given wrap_func."""
        new_node = ast.Call(
            ast.Name(self._wrap_func, ast.Load()),
            args=[node.func, *node.args],
            keywords=node.keywords
        )

        ast.copy_location(new_node, node)
        self.generic_visit(node)
        return new_node

    def visit_FunctionDef(self, node):
        # Remove decorator if provided to prevent recursion.
        if self._dec_name is not None:
            new_deco_list = [val for val in node.decorator_list if self._not_deco_target(val)]
            if len(new_deco_list) == len(node.decorator_list):
                raise RuntimeError(f"Decorator named '{self._dec_name}' not found.")
            node.decorator_list = new_deco_list

        # Add measure func as last param.
        node.args.kwonlyargs.append(ast.arg(self._wrap_func))
        node.args.kw_defaults.append(None)
        # print("args", node.args)

        self.generic_visit(node)
        return node

    def _not_deco_target(self, node):
        match node:
            case ast.Name(id=id):
                return id != self._dec_name
            case ast.Call(func=ast.Name(id=id)):
                return id != self._dec_name
            case _:
                raise RuntimeError(f"Decorator type {node.__class__.__name__} not supported.")
