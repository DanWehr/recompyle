"""
Tests that serve as examples for wrapping different kinds if functions and methods.
"""
import logging

import pytest

from recompyle import rewrite_wrap_calls

log = logging.getLogger(__name__)


def basic_wrapper(call, *args, **kwargs):
    """Basic wrapper that creates two logs per call."""
    log.info(f"Before {call.__qualname__}")
    try:
        return call(*args, **kwargs)
    finally:
        log.info(f"After {call.__qualname__}")


@rewrite_wrap_calls(wrap_call=basic_wrapper)
def example_function(count, secondary):
    for _ in (int(v) for v in range(count)):
        pass
    return secondary()

def secondary_function():
    return True

class ExampleClass:
    @rewrite_wrap_calls(wrap_call=basic_wrapper)
    def example_method(self, count, secondary):
        for _ in (int(v) for v in range(count)):
            pass
        return secondary()

    def secondary_method(self):
        return True

    @classmethod
    @rewrite_wrap_calls(wrap_call=basic_wrapper)
    def example_classmethod(cls, count, secondary):
        for _ in (int(v) for v in range(count)):
            pass
        return secondary()

    @classmethod
    def secondary_classmethod(cls):
        return True

    @staticmethod
    @rewrite_wrap_calls(wrap_call=basic_wrapper)
    def example_staticmethod(count, secondary):
        for _ in (int(v) for v in range(count)):
            pass
        return secondary()

    @staticmethod
    def secondary_staticmethod():
        return True


class TestBasicWrapper:
    COUNT = 5

    @pytest.mark.parametrize(
        "func", [example_function, ExampleClass().example_method, ExampleClass.example_classmethod, ExampleClass.example_staticmethod],
    )
    @pytest.mark.parametrize(
        "secondary", [secondary_function, ExampleClass().secondary_method, ExampleClass.secondary_classmethod, ExampleClass.secondary_staticmethod],
    )
    def test_wrap_secondary_combinations(self, func, secondary, caplog):
        """Verify wrapped functions run and log correctly."""
        with caplog.at_level(logging.INFO):
            assert func(TestBasicWrapper.COUNT, secondary)
        assert len(caplog.records) == (TestBasicWrapper.COUNT * 2) + 4
