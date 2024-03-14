import logging

import pytest

from recompyle import CallExtras, wrap_calls

log = logging.getLogger(__name__)


def basic_wrapper(__call, __extras: CallExtras, *args, **kwargs):
    """Basic wrapper that creates two logs per call."""
    log.info(f"{__extras['ln_range']} {__extras['source']}")
    return __call(*args, **kwargs)


def unrelated_decorator(func):
    return func


@unrelated_decorator
@wrap_calls(wrapper=basic_wrapper)
def example_function(count):
    for v in range(count):
        int(
            v,
        )


# THE TESTS BELOW ARE FRAGILE TESTS AS WE ARE VERIFYING LINE NUMBERS
# MOVING ANY LINES ABOVE WILL BREAK AT LEAST ONE TEST


class TestWrapperExtras:
    COUNT = 2

    def test_wrap_extras(self, caplog):
        with caplog.at_level(logging.INFO):
            example_function(TestWrapperExtras.COUNT)

        msgs = [log.message for log in caplog.records]
        expected = [
            "(23,) range(count)",
            "(24, 26) int(v)",
            "(24, 26) int(v)",
        ]
        assert msgs == expected
