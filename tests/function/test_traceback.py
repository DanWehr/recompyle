import traceback

import pytest

from recompyle import wrap_calls


def wrapper_with_exc(__call, *args, **kwargs):
    raise ValueError("TestErr")


def wrapper_no_exc(__call, *args, **kwargs):
    return __call(*args, **kwargs)


def secondary_with_exc():
    raise ValueError("TestErr")


def secondary_no_exc():
    pass


@wrap_calls(wrapper=wrapper_with_exc)
def func_with_wrapper_exc():
    secondary_no_exc()


@wrap_calls(wrapper=wrapper_no_exc)
def func_with_inner_exc():
    secondary_no_exc()
    raise ValueError("TestErr")


@wrap_calls(wrapper=wrapper_no_exc)
def func_with_deeper_exc():
    secondary_with_exc()


# THE TESTS BELOW ARE FRAGILE TESTS AS WE ARE VERIFYING LINE NUMBERS
# MOVING ANY LINES ABOVE WILL BREAK AT LEAST ONE TEST


class TestWrapperTracebackDetails:
    """Verify tracebacks, especially correct line number in the wrapped function."""

    def summarize_frames(self, tb, limit):
        while tb.tb_next:
            tb = tb.tb_next
        summary = traceback.StackSummary.extract(traceback.walk_stack(tb.tb_frame), limit=limit)
        return [(frame.name, frame.lineno, frame.line) for frame in summary][::-1]

    def test_with_wrapper_exc(self):
        with pytest.raises(ValueError, match="TestErr") as exc_info:
            func_with_wrapper_exc()

        tups = self.summarize_frames(exc_info.tb, 2)
        assert tups[0] == ("func_with_wrapper_exc", 26, "secondary_no_exc()")
        assert tups[1] == ("wrapper_with_exc", 9, 'raise ValueError("TestErr")')

    def test_with_inner_exc(self):
        """Exception in wrapped function has correct line number."""
        with pytest.raises(ValueError, match="TestErr") as exc_info:
            func_with_inner_exc()

        tups = self.summarize_frames(exc_info.tb, 1)
        assert tups[0] == ("func_with_inner_exc", 32, 'raise ValueError("TestErr")')

    def test_with_deeper_exc(self):
        """Wrapper is part of traceback."""
        with pytest.raises(ValueError, match="TestErr") as exc_info:
            func_with_deeper_exc()

        tups = self.summarize_frames(exc_info.tb, 3)
        assert tups[0] == ("func_with_deeper_exc", 37, "secondary_with_exc()")
        assert tups[1] == ("wrapper_no_exc", 13, "return __call(*args, **kwargs)")
        assert tups[2] == ("secondary_with_exc", 17, 'raise ValueError("TestErr")')
