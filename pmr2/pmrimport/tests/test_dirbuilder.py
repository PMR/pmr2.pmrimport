import unittest
import sys
import os, os.path
import shutil
import tempfile
from cStringIO import StringIO

from pmr2.pmrimport.builder import *


class BaseCellMLBuilderTestCase(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.builder = CellMLBuilder(self.workdir, '')

    def tearDown(self):
        pass

    def test_breakuri_error(self):
        tests = (
            'invaliduri', # plain
            'invalid_url', 
        )

        for i in tests:
            self.assertRaises(ValueError, self.builder.breakuri, i)

    def test_breakuri_valid(self):
        tests = (
            ('authorA_1977_version01', 
                ('authorA_1977', '01', None, None)),
            ('author_authorb_1977_version01', 
                ('author_authorb_1977', '01', None, None)),
            ('author_authorb_1977_version06_variant02', 
                ('author_authorb_1977', '06', 'variant02', None)),
            ('author_authorb_1977_version02_variant12', 
                ('author_authorb_1977', '02', 'variant12', None)),
            ('author_boy_cat_dog_2001_version09_variant02', 
                ('author_boy_cat_dog_2001', '09', 'variant02', None)),
            ('nobody_0000_version09_variant02_part01', 
                ('nobody_0000', '09', 'variant02', 'part01')),
            ('sine-approximation_version01_variant02', 
                ('sine-approximation', '01', 'variant02', None)),
        )

        for i, o in tests:
            self.assertEqual(self.builder.breakuri(i), o,
                "input '%s' failed" % i)

    def test_prepare_cellml_path(self):
        uri = 'http://www.cellml.org/models/beeler_reuter_1977_version01'
        self.builder.uri = uri
        result = self.builder.prepare_cellml_path()
        citation, version, variant, part = \
            self.builder.breakuri(os.path.basename(uri))
        self.assert_(os.path.isdir(os.path.join(
            self.workdir, os.path.basename(citation))))
        self.assert_(os.path.isdir(os.path.join(
            self.workdir, citation, version)))
        self.assert_(os.path.isdir(os.path.join(
            self.workdir, citation, version)))
        self.assertEqual(result, os.path.join(
            self.workdir, citation, version, 'beeler_reuter_1977.cellml'))


class MainCellMLBuilderTestCase(unittest.TestCase):
    """\
    Will use the PMR instance, but only partial list of files supplied here.
    """

    uris = [
        'http://www.cellml.org/models/beeler_reuter_1977_version01',
        'http://www.cellml.org/models/beeler_reuter_1977_version02',
        'http://www.cellml.org/models/beeler_reuter_1977_version03',
        'http://www.cellml.org/models/beeler_reuter_1977_version04',
        'http://www.cellml.org/models/beeler_reuter_1977_version05',
        'http://www.cellml.org/models/beeler_reuter_1977_version06',
        'http://www.cellml.org/models/beeler_reuter_1977_version07',
        'http://www.cellml.org/models/beeler_reuter_1977_version08',
        'http://www.cellml.org/models/bental_2006_version02_variant03',
        'http://www.cellml.org/models/bental_2006_version02_variant02',
        'http://www.cellml.org/models/bental_2006_version02_variant01',
        'http://www.cellml.org/models/bental_2006_version02',
        'http://www.cellml.org/models/bental_2006_version01_variant03',
        'http://www.cellml.org/models/bental_2006_version01_variant02',
        'http://www.cellml.org/models/bental_2006_version01_variant01',
        'http://www.cellml.org/models/bental_2006_version01',
    ]

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.builder = CellMLBuilder(self.workdir, '')

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_run_basic(self):
        uri = self.uris[0]  # beeler_reuter_1977_version01
        self.builder.uri = uri
        self.builder.run()
        f = open(self.builder.get_result('dest')).read()
        self.assert_('<model ' in f)

    def test_run_variant(self):
        uri = self.uris[8]  # bental_2006_version02_variant03
        self.builder.uri = uri
        self.builder.run()
        f = open(self.builder.get_result('dest')).read()
        self.assert_('<model ' in f)


class LiveCellMLBuilderTestCase(unittest.TestCase):
    """\
    Will use the full, live PMR instance.
    """

    # globals to reduce re-downloading stuff
    urilist = []

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.builder = CellMLBuilder(self.workdir, [])

    def tearDown(self):
        pass

    def test_001_breakuri(self):
        urilist = get_pmr_urilist()
        LiveCellMLBuilderTestCase.urilist = urilist
        output = [self.builder.breakuri(os.path.basename(i)) for i in urilist]
        self.assertEqual(len(urilist), len(output))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BaseCellMLBuilderTestCase))
    suite.addTest(unittest.makeSuite(MainCellMLBuilderTestCase))
    suite.addTest(unittest.makeSuite(LiveCellMLBuilderTestCase))
    return suite

def cmd_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BaseCellMLBuilderTestCase))
    suite.addTest(unittest.makeSuite(MainCellMLBuilderTestCase))
    if testlive:
        suite.addTest(unittest.makeSuite(LiveCellMLBuilderTestCase))
    return suite

if __name__ == '__main__':
    args = sys.argv[1:]
    testlive = args and args[-1:] or None
    if testlive is not None:
        if testlive[0] == '1':
            sys.argv.pop()
        else:
            testlive = False
    unittest.main(defaultTest='cmd_suite')

