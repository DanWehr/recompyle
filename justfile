[default]
help:
    @just --list

build:
    uv build --wheel

# Test all python versions
test-all: test-310 test-311 test-312 test-313 test-314

test-310 *args:
    uv run --python=3.10 pytest {{args}}

test-311 *args:
    uv run --python=3.11 pytest {{args}}

test-312 *args:
    uv run --python=3.12 pytest {{args}}

test-313 *args:
    uv run --python=3.13 pytest {{args}}

test-314 *args:
    uv run --python=3.14 pytest {{args}}

test-310-cov *args: && cov-report
    uv run --python=3.10 coverage run --branch -m pytest {{args}}

test-311-cov *args: && cov-report
    uv run --python=3.11 coverage run --branch -m pytest {{args}}

test-312-cov *args: && cov-report
    uv run --python=3.12 coverage run --branch -m pytest {{args}}

test-313-cov *args: && cov-report
    uv run --python=3.13 coverage run --branch -m pytest {{args}}

test-314-cov *args: && cov-report
    uv run --python=3.14 coverage run --branch -m pytest {{args}}

cov-report:
    uv run coverage report

sync-310:
    uv sync --python=3.10

sync-311:
    uv sync --python=3.11

sync-312:
    uv sync --python=3.12

sync-313:
    uv sync --python=3.13

sync-314:
    uv sync --python=3.14
