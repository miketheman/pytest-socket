import pytest
from pytest_socket import enable_socket

pytest_plugins = 'pytester'


@pytest.fixture(autouse=True)
def reenable_socket():
    # The tests can leave the socket disabled in the global scope.
    # Fix that by automatically re-enabling it after each test
    yield
    enable_socket()
