"""
Tests for function call wrapping that control which calls get wrapped.
"""
import logging

from recompyle import rewrite_wrap_calls

log = logging.getLogger(__name__)


def basic_wrapper(call, *args, **kwargs):
    """Basic wrapper that creates two logs per call."""
    log.info(f"Before {call.__qualname__}")
    try:
        return call(*args, **kwargs)
    finally:
        log.info(f"After {call.__qualname__}")


def other_function():
    return


@rewrite_wrap_calls(wrap_call=basic_wrapper, ignore_builtins=True)
def with_builtins():
    for _ in (int(v) for v in range(5)):
        pass
    other_function()
    return True


class C:
    def c_1(self):
        return False

    def c_2(self):
        return True


class B:
    c = C()


class A:
    b = B()


@rewrite_wrap_calls(wrap_call=basic_wrapper, ignore_custom={"A", "a.b.c.c_2"})
def with_attributes():
    a = A()
    a.b.c.c_1()
    return a.b.c.c_2()


class TestIgnoreCalls:
    def test_ignore_builtins(self, caplog):
        """Verify builtin callables like int and range are ignored with ignore_builtins."""
        with caplog.at_level(logging.INFO):
            assert with_builtins()
        assert len(caplog.records) == 2
        for record in caplog.records:
            assert "other_function" in record.message

    def test_ignore_custom(self, caplog):
        """Verify custom ignore works including nested attributes."""
        with caplog.at_level(logging.INFO):
            assert with_attributes()
        assert len(caplog.records) == 2
        for record in caplog.records:
            assert "C.c_1" in record.message  # Qualname is used, doesn't have the full path.
