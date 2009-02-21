import unittest
import os
from os.path import dirname, join
from cStringIO import StringIO

from pmr2.pmrimport.builder import *


class RootTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic(self):
        o = DirBuilder('tmp', [])
        o = WorkspaceBuilder('source', 'dest')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RootTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()

