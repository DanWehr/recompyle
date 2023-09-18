"""
Tests/examples for wrapping different kinds if functions and methods.
"""
import logging

import pytest

from recompyle import wrap_calls

log = logging.getLogger(__name__)


def basic_wrapper(__call, *args, **kwargs):
    """Basic wrapper that creates two logs per call."""
    log.info(f"Before {__call.__qualname__}")
    try:
        return __call(*args, **kwargs)
    finally:
        log.info(f"After {__call.__qualname__}")


@wrap_calls(wrapper=basic_wrapper)
def example_function(count, secondary):
    for _ in (int(v) for v in range(count)):
        pass
    return secondary()


def secondary_function():
    return True


class ExampleClass:
    @wrap_calls(wrapper=basic_wrapper)
    def example_method(self, count, secondary):
        for _ in (int(v) for v in range(count)):
            pass
        return secondary()

    def secondary_method(self):
        return True

    @classmethod
    @wrap_calls(wrapper=basic_wrapper)
    def example_classmethod(cls, count, secondary):
        for _ in (int(v) for v in range(count)):
            pass
        return secondary()

    @classmethod
    def secondary_classmethod(cls):
        return True

    @staticmethod
    @wrap_calls(wrapper=basic_wrapper)
    def example_staticmethod(count, secondary):
        for _ in (int(v) for v in range(count)):
            pass
        return secondary()

    @staticmethod
    def secondary_staticmethod():
        return True


def outer_nested():
    @wrap_calls(wrapper=basic_wrapper)
    def inner_nested():
        return int(1.23)

    return inner_nested()


class TestBasicWrapper:
    COUNT = 5

    @pytest.mark.parametrize(
        "func",
        [
            example_function,
            ExampleClass().example_method,
            ExampleClass.example_classmethod,
            ExampleClass.example_staticmethod,
        ],
    )
    @pytest.mark.parametrize(
        "secondary",
        [
            secondary_function,
            ExampleClass().secondary_method,
            ExampleClass.secondary_classmethod,
            ExampleClass.secondary_staticmethod,
        ],
    )
    def test_wrap_secondary_combinations(self, func, secondary, caplog):
        """Verify wrapped functions run and create the expected number of logs."""
        with caplog.at_level(logging.INFO):
            assert func(TestBasicWrapper.COUNT, secondary)
        assert len(caplog.records) == (TestBasicWrapper.COUNT * 2) + 4

    def test_wrap_nested(self, caplog):
        """Nested functions can be wrapped if they don't use nonlocals."""
        with caplog.at_level(logging.INFO):
            assert outer_nested() == 1
        assert caplog.records[0].message == "Before int"
        assert caplog.records[1].message == "After int"
