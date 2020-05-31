=============
pytest-socket
=============

This document records all notable changes to `pytest-socket <https://pypi.python.org/pypi/pytest-socket>`_.
This project attempts to adhere to `Semantic Versioning <http://semver.org/>`_.

`0.3.5`_ (2020-05-31)
---------------------

Bugfix release.

* Fix bug in marker evaluation #42
* Refactor tests for clarity

`0.3.4`_ (2020-04-10)
---------------------

Maintenance release.

* Drop support for unsupported versions of Python #23
* Convert toolchain from pip/tox/twine to poetry
* Replace TravisCI and Appveyor with GitHub Actions #36
* Update for correct test output #31
* Add renovatebot for dependecy updates #26

`0.3.3`_ (2019-02-09)
---------------------

* Fix hostname check when unicode on Python 2.7.x #22

`0.3.2`_ (2019-01-07)
---------------------

* Update support for Pytest 4.1.x
* Test package on Python 3.7.x
* Stop testing on pypy

`0.3.1`_ (2018-07-16)
---------------------

* Update minimum required pytest version

`0.3.0`_ (2018-07-15)
---------------------

* Add support for allowing specific lists of hosts via IP Addresses
* Change the inherited exception class in tests
* Add codeclimate to travis output
* Add coverage reporting
* Drop support for Python 3.3

`0.2.0`_ (2017-07-15)
---------------------

* Reorganized API, requires explicit activation
* Added Python 3.x compatibility
* Added ``ini`` setting
* Test all Python versions
* Relax py.test version requirement


`0.1.0`_ (2017-06-01)
---------------------

* Initial public release


.. _0.1.0: https://github.com/miketheman/pytest-socket/releases/tag/0.1.0
.. _0.2.0: https://github.com/miketheman/pytest-socket/compare/0.1.0...0.2.0
.. _0.3.0: https://github.com/miketheman/pytest-socket/compare/0.2.0...0.3.0
.. _0.3.1: https://github.com/miketheman/pytest-socket/compare/0.3.0...0.3.1
.. _0.3.2: https://github.com/miketheman/pytest-socket/compare/0.3.1...0.3.2
.. _0.3.3: https://github.com/miketheman/pytest-socket/compare/0.3.2...0.3.3
.. _0.3.4: https://github.com/miketheman/pytest-socket/compare/0.3.3...0.3.4
.. _0.3.5: https://github.com/miketheman/pytest-socket/compare/0.3.4...0.3.5
