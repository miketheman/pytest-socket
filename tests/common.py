"""
Common test functions.
"""


def assert_socket_blocked(result, passed=0, skipped=0, failed=1):
    """
    Uses built in methods to test for common failure scenarios.
    Usually we only test for a single failure,
    but sometimes we want to test for multiple conditions,
    so we can pass in the expected counts.
    """
    result.assert_outcomes(passed=passed, skipped=skipped, failed=failed)
    result.stdout.fnmatch_lines(
        "*Socket*Blocked*Error: A test tried to use socket.socket.*"
    )
