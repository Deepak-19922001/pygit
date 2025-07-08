#!/usr/bin/env python3

import unittest
import sys
import os
from test_pygit import PyGitTest

if __name__ == "__main__":
    print("=== Running PyGit Test Suite ===")
    
    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(PyGitTest)
    
    # Run the tests
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # Exit with appropriate code
    if result.wasSuccessful():
        print("\n=== All tests passed! ===")
        sys.exit(0)
    else:
        print("\n=== Some tests failed! ===")
        sys.exit(1)