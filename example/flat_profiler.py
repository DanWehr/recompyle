import logging
import time

from recompyle import flat_profile

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def slow_function(val: float) -> str:
    """Slow function being called."""
    time.sleep(0.5)  # Force total time of example_function over limit
    return f"other val: {val}"


def faster_function() -> None:
    """Faster function being called."""
    time.sleep(0.001)


@flat_profile(time_limit=0.3)
def example_function(count: int) -> str:
    """Function we are rewriting to time calls."""
    faster_function()
    for _ in (int(v) for v in range(count)):
        pass
    return slow_function(val=123.45)


log.info(example_function(2))
