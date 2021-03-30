=============
pytest-socket
=============

.. image:: https://img.shields.io/pypi/v/pytest-socket.svg
    :target: https://pypi.python.org/pypi/pytest-socket

.. image:: https://img.shields.io/pypi/pyversions/pytest-socket.svg
    :target: https://pypi.python.org/pypi/pytest-socket

.. image:: https://github.com/miketheman/pytest-socket/workflows/Python%20Tests/badge.svg
    :target: https://github.com/miketheman/pytest-socket/actions?query=workflow%3A%22Python+Tests%22
    :alt: Python Tests

.. image:: https://api.codeclimate.com/v1/badges/1608a75b1c3a20211992/maintainability
   :target: https://codeclimate.com/github/miketheman/pytest-socket/maintainability
   :alt: Maintainability

.. image:: https://app.fossa.io/api/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket.svg?type=shield
   :target: https://app.fossa.io/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket?ref=badge_shield
   :alt: FOSSA Status


A plugin to use with Pytest to disable or restrict ``socket`` calls during tests to ensure network calls are prevented.

----

This `Pytest`_ plugin was generated with `Cookiecutter`_ along with `@hackebrot`_'s `Cookiecutter-pytest-plugin`_ template.


Features
--------

* Disables all network calls flowing through Python's ``socket`` interface.


Requirements
------------

* `Pytest`_ 3.6.3 or greater


Installation
------------

You can install "pytest-socket" via `pip`_ from `PyPI`_::

    $ pip install pytest-socket


Usage
-----

* Run ``pytest --disable-socket``, tests should fail on any access to ``socket`` or libraries using
  socket with a ``SocketBlockedError``.

  To add this flag as the default behavior, add this section to your ``pytest.ini`` or ``setup.cfg``:

  .. code:: ini

    [pytest]
    addopts = --disable-socket


  or update your ``conftest.py`` to include:

  .. code:: python

    from pytest_socket import disable_socket

    def pytest_runtest_setup():
        disable_socket()

* To enable Unix sockets during the test run (e.g. for async), add this option:

.. code:: ini

  [pytest]
  addopts = --disable-socket --allow-unix-socket

* To enable specific tests use of ``socket``, pass in the fixture to the test or use a marker:

  .. code:: python

    def test_explicitly_enable_socket(socket_enabled):
        assert socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    @pytest.mark.enable_socket
    def test_explicitly_enable_socket_with_mark():
        assert socket.socket(socket.AF_INET, socket.SOCK_STREAM)

* To allow only specific hosts per-test:

  .. code:: python

    @pytest.mark.allow_hosts(['127.0.0.1'])
    def test_explicitly_enable_socket_with_mark():
        assert socket.socket.connect(('127.0.0.1', 80))

or for whole test run

  .. code:: ini

    [pytest]
    addopts = --allow-hosts=127.0.0.1,127.0.1.1

Frequently Asked Questions
==========================

Q: Why is network access disabled in some of my tests but not others?

A: pytest's default fixture scope is "function", which ``socket_enabled`` uses.
If you create another fixture that creates a socket usage that has a "higher"
instantiation order, such as at the module/class/session, then the higher
fixture will be resolved first, and won't be disabled during the tests.
Read more in `this excellent example
<https://github.com/miketheman/pytest-socket/issues/45#issue-679835420>`_ and
more about `pytest fixture order here <https://docs.pytest.org/en/stable/fixture.html#fixture-instantiation-order>`_.

This behavior may change in the future, as we learn more about pytest fixture
order, and what users expect to happen.

Contributing
------------
Contributions are very welcome. Tests can be run with `pytest`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-socket" is free and open source software

.. image:: https://app.fossa.io/api/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket.svg?type=large
   :target: https://app.fossa.io/projects/git%2Bgithub.com%2Fmiketheman%2Fpytest-socket?ref=badge_large
   :alt: FOSSA Status

Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.


References
----------

This plugin came about due to the efforts by `@hangtwenty`_ solving a `StackOverflow question`_,
then converted into a pytest plugin by `@miketheman`_.


.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/miketheman/pytest-socket/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi
.. _`@hangtwenty`: https://github.com/hangtwenty
.. _`StackOverflow question`: https://stackoverflow.com/a/30064664
.. _`@miketheman`: https://github.com/miketheman
