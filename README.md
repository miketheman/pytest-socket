# pytest-socket

[![PyPI current version](https://img.shields.io/pypi/v/pytest-socket.svg)](https://pypi.python.org/pypi/pytest-socket)
[![Python Support](https://img.shields.io/pypi/pyversions/pytest-socket.svg)](https://pypi.python.org/pypi/pytest-socket)
[![Tests](https://github.com/miketheman/pytest-socket/workflows/Python%20Tests/badge.svg)](https://github.com/miketheman/pytest-socket/actions?query=workflow%3A%22Python+Tests%22)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/miketheman/pytest-socket/main.svg)](https://results.pre-commit.ci/latest/github/miketheman/pytest-socket/main)
[![Maintainability](https://api.codeclimate.com/v1/badges/1608a75b1c3a20211992/maintainability)](https://codeclimate.com/github/miketheman/pytest-socket/maintainability)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket?ref=badge_shield)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A plugin to use with Pytest to disable or restrict `socket` calls during
tests to ensure network calls are prevented.

---

## Features

- Disables all network calls flowing through Python\'s `socket` interface.

## Requirements

- [Pytest](https://github.com/pytest-dev/pytest) 6.2.5 or greater

## Installation

You can install `pytest-socket` via [pip](https://pypi.python.org/pypi/pip/)
from [PyPI](https://pypi.python.org/pypi):

```console
pip install pytest-socket
```

or add to your `pyproject.toml` for [poetry](https://python-poetry.org/):

```ini
[tool.poetry.dev-dependencies]
pytest-socket = "*"
```

## Usage

Run `pytest --disable-socket`, tests should fail on any access to `socket` or
libraries using socket with a `SocketBlockedError`.

To add this flag as the default behavior, add this section to your
[`pytest.ini`](https://docs.pytest.org/en/6.2.x/customize.html#pytest-ini):

```ini
[pytest]
addopts = --disable-socket
```

or add this to your [`setup.cfg`](https://docs.pytest.org/en/6.2.x/customize.html#setup-cfg):

```ini
[tool:pytest]
addopts = --disable-socket
```

or update your [`conftest.py`](https://docs.pytest.org/en/6.2.x/writing_plugins.html#conftest-py-plugins) to include:

```python
from pytest_socket import disable_socket

def pytest_runtest_setup():
    disable_socket()
```

If you exceptionally want to enable socket for one particular execution
pass `--force-enable-socket`. It takes precedence over `--disable-socket`.

To enable Unix sockets during the test run (e.g. for async), add this option:

```ini
[pytest]
addopts = --disable-socket --allow-unix-socket
```

To enable specific tests use of `socket`, pass in the fixture to the test or
use a marker:

```python
def test_explicitly_enable_socket(socket_enabled):
    assert socket.socket(socket.AF_INET, socket.SOCK_STREAM)


@pytest.mark.enable_socket
def test_explicitly_enable_socket_with_mark():
    assert socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```

To allow only specific hosts per-test:

```python
@pytest.mark.allow_hosts(['127.0.0.1'])
def test_explicitly_enable_socket_with_mark():
    assert socket.socket.connect(('127.0.0.1', 80))
```

or for whole test run

```ini
[pytest]
addopts = --allow-hosts=127.0.0.1,127.0.1.1
```

### Frequently Asked Questions

Q: Why is network access disabled in some of my tests but not others?

A: pytest's default fixture scope is "function", which `socket_enabled` uses.
If you create another fixture that creates a socket usage that has a "higher"
instantiation order, such as at the module/class/session, then the higher order
fixture will be resolved first, and won't be disabled during the tests.
Read more in [this excellent example](https://github.com/miketheman/pytest-socket/issues/45#issue-679835420)
and more about [pytest fixture order here](https://docs.pytest.org/en/stable/fixture.html#fixture-instantiation-order).

This behavior may change in the future, as we learn more about pytest
fixture order, and what users expect to happen.

## Contributing

Contributions are very welcome. Tests can be run with
[pytest](https://github.com/pytest-dev/pytest), please ensure the
coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the
[MIT](http://opensource.org/licenses/MIT) license, "pytest-socket" is
free and open source software

[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket?ref=badge_large)

## Issues

If you encounter any problems, please [file an issue](https://github.com/miketheman/pytest-socket/issues)
along with a detailed description.

## References

This [Pytest](https://github.com/pytest-dev/pytest) plugin was generated with
[Cookiecutter](https://github.com/audreyr/cookiecutter) along with
[\@hackebrot](https://github.com/hackebrot)\'s
[Cookiecutter-pytest-plugin](https://github.com/pytest-dev/cookiecutter-pytest-plugin)
template.

This plugin came about due to the efforts by
[\@hangtwenty](https://github.com/hangtwenty) solving a [StackOverflow
question](https://stackoverflow.com/a/30064664), then converted into a
pytest plugin by [\@miketheman](https://github.com/miketheman).
