import logging
import time
from flat_profiler import flat_call_profiler

log = logging.getLogger(__name__)


class Test:
    test_str = "Test String"

    @flat_call_profiler(time_limit=0)
    def secondary_func(self, target, multiplier):
        return {k: v * multiplier for k, v in target.items()}

    @flat_call_profiler(time_limit=0)
    def main_func(self, multiplier):
        # Create a simple dict
        d = {val: str(val) for val in range(10)}
        # Remove a few things from it.
        del d[2]
        d.pop(6)
        time.sleep(5)
        # self.err_call()
        d = self.secondary_func(d, multiplier=multiplier)
        print(d)

    def err_call(self):
        raise ValueError("Test")


if __name__ == "__main__":
    t = Test()
    print("External", t.main_func, t.main_func.__qualname__)
    t.main_func(multiplier=4)
