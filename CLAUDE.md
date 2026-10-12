# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

pytest-socket is a pytest plugin that blocks or restricts `socket` calls during tests. The whole plugin is `src/pytest_socket/__init__.py`; it monkey-patches `socket.socket`, `socket.socket.connect`, `getaddrinfo` and `gethostbyname`, and `pytest_runtest_setup` decides per-test behavior by precedence (enable > disable > allow_hosts > global `--disable-socket`).

## Testing

`make test` runs the suite with coverage. `pytest-randomly` shuffles order; reproduce with the printed `--randomly-seed=<seed>` or disable with `-p no:randomly`.

```bash
# Another interpreter, without disturbing .venv (e.g. 3.15, 3.14t)
UV_PROJECT_ENVIRONMENT=/tmp/venv315 uv run -p 3.15 pytest
```

Most tests run pytest in-process via `pytester.makepyfile()` + `pytester.runpytest()`; a few call `disable_socket()` / `enable_socket()` directly for behavior the in-process runner can't reach.

mypy is **not** a pre-commit hook; CI runs it separately, so run `uv run mypy src` before pushing.

## Mutation testing

`make mutmut` fails on any surviving mutant. Mutating the plugin's own pytest hooks crashes the inner pytest, so roughly 20 mutants report `segfault` (count varies run to run); the gate tolerates those. mutmut lives in its own `mutmut` dependency group, not `dev`: its libcst dependency lags new Python releases and has no 3.13t wheel.

## CI

- `.github/workflows/python.yml` passes the matrix version to setup-uv's `python-version` (sets `UV_PYTHON` and the cache key). Don't go back to a separate `uv python install` step: `uv sync` ignores it and falls back to the system Python. Check a job log's `Using CPython ...` line to confirm the interpreter.
- Adding a Python version: the matrix in `python.yml`, the classifier in `pyproject.toml`, and the single version in `codspeed.yml`. CodSpeed can't run the same benchmarks across a version matrix, so move it rather than adding a second version.
- `zizmor .github/workflows/` audits workflow changes locally; CI runs it too.

## Commits

Conventional-commit subjects (`chore(ci):`, `chore(deps):`, `fix:`, `feat:`, `test:`), signed off with `git commit -s`.
