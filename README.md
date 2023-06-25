# Recompyle

This package provides tools that can be used to rewrite and recompile source code, using the transformed version of the code at runtime. The initial proof-of-concept targets functions only, but this project is structured to eventually expand to other code types.

## Installation

[Not Yet Hosted]

## Usage

### The `rewrite_wrap_calls` decorator

[Not Yet Written]

### The `shallow_call_profiler` decorator

[Not Yet Written]

## Background

Recompyle was born from wanting to monitor execution time of a function in production to detect abnormal execution times, while providing more detail than a simple decorator that just records the execution time of the entire function. We want to know *what* in the function was responsible to help with debugging/optimizing.

A full call stack would be the most useful through tools like the builtin `cProfile`, but this has enough overhead that it is not feasible for use in production. One way to address that overhead would be to only periodically profile the program (such as in statistical profiling), but that is primarily useful for improving your typical execution times. If you want to watch for abnormal cases like a slowdown that is rarely caused by an external resource, you want to be able to monitor the execution of the relevant code contunuously.

### Shallow Profiler

Recompyle attempts to address this with a "shallow profiler" (`recompyle.shallow_call_profiler`) that will capture the execution times of *all* calls within a decorated function, and *only* the calls within that function. It does not go deeper and profile the full call stack. Reduced overhead was the primary goal for this proof-of-concept.

The shallow profiler simply records call times, and if the total execution time of the decorated call is greater than a configurable time limit, the times of all internal calls will be logged in addition to the total.

### Recompiling Functions

[Not Yet Written]

## Limitations

- The rewrite+recompile process can only be applied to functions for which you have source access. Applying it through decorators enforces this.
- The current implementation will lose nonlocal variables during the rewrite, so this does not support rewriting inner functions.
- By rewriting a function, the code shown in the traceback of an exception within that function may no longer match the original source. This may be solveable (see future enhancements).

## Future Enhancements

- Investigate optional support for modifying tracebacks to remove the callable wrapper (trace frame and text of source lines) such that the traceback matches original source again.

## Development

[Not Yet Written]
