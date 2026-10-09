# -*- coding: ascii -*-

from doctest import DocFileSuite
import unittest
import os.path
import sys

THIS_DIR = os.path.dirname(__file__)

README = os.path.abspath(
    os.path.join(THIS_DIR, os.pardir, os.pardir, 'README.rst'))
if not os.path.exists(README):
    # Installed-wheel layout: the repository/sdist root README.rst is not
    # two directories above the package. The fork ships a copy inside the
    # package so this test runs against installed wheels too.
    README = os.path.abspath(
        os.path.join(THIS_DIR, os.pardir, 'README.rst'))


class DocumentationTestCase(unittest.TestCase):
    def test_readme_encoding(self):
        '''Confirm the README.rst is ASCII.'''
        f = open(README, 'rb')
        try:
            f.read().decode('ASCII')
        finally:
            f.close()


def test_suite():
    "For the Z3 test runner"
    return unittest.TestSuite((
        DocumentationTestCase('test_readme_encoding'),
        DocFileSuite(README, module_relative=False)))


if __name__ == '__main__':
    sys.path.insert(
        0, os.path.abspath(os.path.join(THIS_DIR, os.pardir, os.pardir))
    )
    unittest.main(defaultTest='test_suite')
