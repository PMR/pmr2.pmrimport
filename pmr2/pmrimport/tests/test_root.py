import unittest
import os
from os.path import dirname, join
from cStringIO import StringIO


class RootTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RootTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()

