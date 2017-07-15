=============
pytest-socket
=============

.. image:: https://img.shields.io/pypi/v/pytest-socket.svg
    :target: https://pypi.python.org/pypi/pytest-socket

.. image:: https://img.shields.io/pypi/pyversions/pytest-socket.svg
    :target: https://pypi.python.org/pypi/pytest-socket

.. image:: https://travis-ci.org/miketheman/pytest-socket.svg?branch=master
    :target: https://travis-ci.org/miketheman/pytest-socket
    :alt: See Build Status on Travis CI

.. image:: https://ci.appveyor.com/api/projects/status/github/miketheman/pytest-socket?branch=master&svg=true
    :target: https://ci.appveyor.com/project/miketheman/pytest-socket/branch/master
    :alt: See Build Status on AppVeyor

A plugin to use with Pytest to disable ``socket`` calls during tests to ensure network calls are prevented.

----

This `Pytest`_ plugin was generated with `Cookiecutter`_ along with `@hackebrot`_'s `Cookiecutter-pytest-plugin`_ template.


Features
--------

* Disables all network calls flowing through Python's ``socket`` interface.


Requirements
------------

* `Pytest`_ 3.0.0 or greater


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


* To enable specific tests use of ``socket``, pass in the fixture to the test or use a marker:

  .. code:: python

    def test_explicitly_enable_socket(socket_enabled):
        assert socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    @pytest.mark.enable_socket
    def test_explicitly_enable_socket_with_mark():
      assert socket.socket(socket.AF_INET, socket.SOCK_STREAM)


Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-socket" is free and open source software


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
