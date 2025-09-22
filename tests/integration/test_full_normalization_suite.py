"""
Full normalization suite - test utilities.
"""

def assert_normalized_name(result, expected, description=""):
    """Assert that normalized name matches expected value."""
    if hasattr(result, 'normalized'):
        actual = result.normalized
    else:
        actual = result

    assert actual == expected, f"{description}: expected '{expected}', got '{actual}'"


def run_normalization_suite():
    """Run the full normalization test suite."""
    pass