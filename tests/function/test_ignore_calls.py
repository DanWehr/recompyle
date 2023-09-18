"""
Tests/examples for call wrapping while limiting which calls get wrapped.
"""
import logging

from recompyle import wrap_calls

log = logging.getLogger(__name__)


def basic_wrapper(__call, *args, **kwargs):
    """Basic wrapper that creates two logs per call."""
    log.info(f"Before {__call.__qualname__}")
    try:
        return __call(*args, **kwargs)
    finally:
        log.info(f"After {__call.__qualname__}")


def other_function():
    return


@wrap_calls(wrapper=basic_wrapper, ignore_builtins=True)
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
    c = {"c": C()}


class A:
    b = [B()]


@wrap_calls(wrapper=basic_wrapper, blacklist={"A", "a.b[0].c[c].c_2"})
def complex_blacklist():
    a = A()
    a.b[0].c["c"].c_1()
    return a.b[0].c["c"].c_2()


@wrap_calls(wrapper=basic_wrapper, blacklist={"a.b[0].c[*].c_2"})
def complex_blacklist_wildcard():
    a = A()
    a.b[0].c["c"].c_1()
    return a.b[0].c["c"].c_2()


@wrap_calls(wrapper=basic_wrapper, whitelist={"a.b[0].c[*].c_1"})
def complex_whitelist_wildcard():
    a = A()
    a.b[0].c["c"].c_1()
    return a.b[0].c["c"].c_2()


class TestIgnoreCalls:
    def test_ignore_builtins(self, caplog):
        """Verify builtin callables like int and range are ignored with ignore_builtins."""
        with caplog.at_level(logging.INFO):
            assert with_builtins() is True
        assert len(caplog.records) == 2
        for record in caplog.records:
            assert "other_function" in record.message

    def test_complex_blacklist(self, caplog):
        """Verify custom blacklist works including nested attributes and subscripts."""
        with caplog.at_level(logging.INFO):
            assert complex_blacklist() is True
        assert len(caplog.records) == 2
        for record in caplog.records:
            assert "C.c_1" in record.message  # Qualname is used, doesn't have the full path.

    def test_complex_blacklist_wildcard(self, caplog):
        """Verify custom blacklist works including nested attributes and subscripts using a wildcard."""
        with caplog.at_level(logging.INFO):
            assert complex_blacklist_wildcard() is True
        assert len(caplog.records) == 4
        for record in caplog.records:
            assert "C.c_1" in record.message or "A" in record.message  # Qualname is logged, doesn't have the full path.

    def test_complex_whitelist_wildcard(self, caplog):
        """Verify custom whitelist works including nested attributes and subscripts using a wildcard."""
        with caplog.at_level(logging.INFO):
            assert complex_whitelist_wildcard() is True
        assert len(caplog.records) == 2
        for record in caplog.records:
            assert "C.c_1" in record.message  # Qualname is logged, doesn't have the full path.
