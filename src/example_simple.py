from call_wrapper import call_wrapper
import time


def simple_logger(func, *args, **kwargs):
    print(f"Before {func.__qualname__}")
    try:
        return func(*args, **kwargs)
    finally:
        print(f"After {func.__qualname__}")


class Test:
    test_str = "Test String"

    def __init__(self):
        self.val = "Test"

    @call_wrapper(wrap_func=simple_logger)
    def secondary_func(self, target, multiplier):
        return {k: v * multiplier for k, v in target.items()}

    @call_wrapper(wrap_func=simple_logger)
    def main_func(self, multiplier):
        # Create a simple dict
        d = {val: str(val) for val in range(10)}
        # Remove a few things from it.
        del d[2]
        d.pop(6)
        time.sleep(5)
        print(self.test_str)
        self.val = "TestModified"
        print(self.val)
        # self.err_call()
        d = self.secondary_func(d, multiplier=multiplier)
        print(d)

    def err_call(self):
        raise ValueError("Test")


if __name__ == "__main__":
    t = Test()
    print("External", t.main_func, t.main_func.__qualname__)
    t.main_func(multiplier=4)
