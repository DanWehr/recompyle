import ast


class RecompyleBaseTransformer(ast.NodeTransformer):
    """Base transformer class that should be used with all Recompyle rewriters.

    Transformers that change the starting line number of function must change adjust_lineno accordingly. For example if
    if the transformer moves the function one line earlier, substract one from adjust_lineno.
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
