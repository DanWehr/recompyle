import ast


class RecompyleBaseTransformer(ast.NodeTransformer):
    """Base transformer class that should be used with all Recompyle rewriters.

    If a transformer does not change line numbers it can leave the value at the default 0.
    """
    def __init__(self) -> None:
        super().__init__()
        self._adjust_lineno: int = 0

    @property
    def adjust_lineno(self) -> int:
        """Get or set the line adjustment for source code after transformations."""
        return self._adjust_lineno

    @adjust_lineno.setter
    def adjust_lineno(self, value: int) -> None:
        self._adjust_lineno = value
