import timeit
from statistics import mean

from recompyle import flat_profile, wrap_calls


def simple_wrapper(__call, *args, **kwargs):
    return __call(*args, **kwargs)


def other(val1, val2):
    return val1 + val2


def unwrapped():
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)


@wrap_calls(wrapper=simple_wrapper)
def wrapped_simple():
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)


@flat_profile(time_limit=100, below_callback=None)
def wrapped_profiler():
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)


@flat_profile(time_limit=100)  # Default below callback will always run
def wrapped_profiler_below():
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)


@flat_profile(time_limit=0)  # Default above callback will always run
def wrapped_profiler_above():
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)
    other(0, val2=1)


count = 100_000
repeat = 100
calls = 10
s_to_us = 1_000_000


def collect_times(stmt, label):
    times = []
    print(f"\rRunning {label} {count:,} times, repeat 0/{repeat}", end="", flush=True)
    # Make our own loop in place of timeit.repeat. Print progress so terminal doesn't appear frozen.
    for loop in range(repeat):
        times.append(timeit.timeit(stmt, number=count, globals=globals()))
        print(f"\rRunning {label} {count:,} times, repeat {loop+1}/{repeat}", end="", flush=True)
    avg = (mean(times) / count) * s_to_us
    print(": average", avg, "microseconds")
    return avg


if __name__ == "__main__":
    base_avg_us = collect_times("unwrapped()", "unwrapped function")
    simple_avg_us = collect_times("wrapped_simple()", "simple wrapper")
    profiler_avg_us = collect_times("wrapped_profiler()", "flat profiler w/ no callback")
    profiler_below_us = collect_times("wrapped_profiler_below()", "flat profiler w/ default below callback")
    profiler_above_us = collect_times("wrapped_profiler_above()", "flat profiler w/ default above callback")

    print("\nSimple wrapper call cost is", (simple_avg_us - base_avg_us) / calls, "microseconds per wrapped call")
    print("Flat profiler call cost is", (profiler_avg_us - base_avg_us) / calls, "microseconds per wrapped call")
    print("Flat profiler default below callback costs", profiler_below_us - profiler_avg_us, "microseconds")
    print("Flat profiler default above callback costs", profiler_above_us - profiler_avg_us, "microseconds")
