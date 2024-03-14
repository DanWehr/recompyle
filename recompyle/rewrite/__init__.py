"""Collect rewrite tools for easier importing."""
from recompyle.rewrite.rewrite_function import (
    CallExtras,
    CallWrapper,
    rewrite_wrap_calls_func,
)

__all__ = ["CallExtras", "CallWrapper", "rewrite_wrap_calls_func"]
