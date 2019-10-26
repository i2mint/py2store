import doctest
import py2store.test.util
import py2store.test.simple


t = doctest.testmod(py2store.test.simple)
print(f"failed={t.failed} attempted={t.attempted}")

# def load_tests(loader, tests, ignore):
#     tests.addTests(doctest.DocTestSuite(py2store.test.util))
#     return tests
#
#
# import unittest
# import os
# from pprint import pprint
#
#
# pprint(unittest.TestLoader().discover(os.path.dirname(__file__)))