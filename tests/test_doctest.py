def test_function_with_doctest(testdir):
    testdir.makepyfile(
        '''
        def my_sum(a, b):
            """Sum two values.

            >>> my_sum(1, 1)
            2
            """
            return a + b
        '''
    )
    result = testdir.runpytest("--doctest-modules")
    result.assert_outcomes(passed=1)
