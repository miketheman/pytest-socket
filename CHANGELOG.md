# pytest-socket change log

This document records all notable changes to
[pytest-socket](https://pypi.python.org/pypi/pytest-socket). This
project attempts to adhere to [Semantic Versioning](http://semver.org/).

## [0.5.1][] (2020-01-23)

### Fixes

- Plugin no longer breaks on `doctests` #109

### Changes

- Dev dependency `starlette` updated
- `make install` now installs dependencies if `poetry.lock` is missing/changed
- Added a GitHub Workflow for stale issues
- pre-commit auto-updated

## [0.5.0][] (2021-12-23)

### Changes

- **Removed support for Python 3.6 and older.**
- Consolidated configuration to `pytest.Config`
- Replaced `autouse` fixture with `pytest_runtest_setup()` #88

### Fixes

- Prevent `IndexError` with `httpx.AsyncClient` #85 (and other frameworks)
- Switched to using `poetry-core` in `pyproject.toml` #74
- Handle family passed as keyword argument #75
- BEhave correctly when passing in multiple configurations #93

### Chores

- Development updates
- Documentation updates
- Applied `black` code formatter
- Applied `isort` import formatter
- Added `pre-commit` hooks and CI status badges
- Fixed code coverage reporting
- Updated Python versions in tests

## [0.4.1][] (2021-08-29)

- Include tests and configs in source distribution archive #69

## [0.4.0][] (2021-03-30)

Enhancements:

- Enable Unix sockets selectively with `--allow-unix-socket` #54
- Test refactor, add CodeQL scanning
- Correctly subclass socket.socket #50
- Add testing against Python 3.9, Dropped testing against Python 3.5
- Doc updates

## [0.3.5][] (2020-05-31)

Bugfix release.

- Fix bug in marker evaluation \#42
- Refactor tests for clarity

## [0.3.4][] (2020-04-10)

Maintenance release.

- Drop support for unsupported versions of Python #23
- Convert toolchain from pip/tox/twine to poetry
- Replace TravisCI and Appveyor with GitHub Actions #36
- Update for correct test output #31
- Add renovatebot for dependency updates #26

## [0.3.3][] (2019-02-09)

- Fix hostname check when unicode on Python 2.7.x #22

## [0.3.2][] (2019-01-07)

- Update support for Pytest 4.1.x
- Test package on Python 3.7.x
- Stop testing on pypy

## [0.3.1][] (2018-07-16)

- Update minimum required pytest version

## [0.3.0][] (2018-07-15)

- Add support for allowing specific lists of hosts via IP Addresses
- Change the inherited exception class in tests
- Add codeclimate to travis output
- Add coverage reporting
- Drop support for Python 3.3

## [0.2.0][] (2017-07-15)

- Reorganized API, requires explicit activation
- Added Python 3.x compatibility
- Added `ini` setting
- Test all Python versions
- Relax py.test version requirement

## [0.1.0] (2017-06-01)

- Initial public release

[0.1.0]: https://github.com/miketheman/pytest-socket/releases/tag/0.1.0
[0.2.0]: https://github.com/miketheman/pytest-socket/compare/0.1.0...0.2.0
[0.3.0]: https://github.com/miketheman/pytest-socket/compare/0.2.0...0.3.0
[0.3.1]: https://github.com/miketheman/pytest-socket/compare/0.3.0...0.3.1
[0.3.2]: https://github.com/miketheman/pytest-socket/compare/0.3.1...0.3.2
[0.3.3]: https://github.com/miketheman/pytest-socket/compare/0.3.2...0.3.3
[0.3.4]: https://github.com/miketheman/pytest-socket/compare/0.3.3...0.3.4
[0.3.5]: https://github.com/miketheman/pytest-socket/compare/0.3.4...0.3.5
[0.4.0]: https://github.com/miketheman/pytest-socket/compare/0.3.5...0.4.0
[0.4.1]: https://github.com/miketheman/pytest-socket/compare/0.4.0...0.4.1
[0.5.0]: https://github.com/miketheman/pytest-socket/compare/0.4.1...0.5.0
[0.5.1]: https://github.com/miketheman/pytest-socket/compare/0.5.0...0.5.1
