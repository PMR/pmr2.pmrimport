import unittest
import sys
import os, os.path
import shutil
import tempfile
from cStringIO import StringIO

from pmr2.pmrimport.builder import *

from mercurial import hg, ui

URIS = [
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

    'http://www.cellml.org/models/noble_varghese_kohl_noble_1998_version06_variant01',
    'http://www.cellml.org/models/noble_varghese_kohl_noble_1998_version07_variant02',
    'http://www.cellml.org/models/tentusscher_noble_noble_panfilov_2004_version03',
]


# XXX bad practice in here
# many of these tests rely on the PMR being online

class DownloadMonitorTestCase(unittest.TestCase):

    def setUp(self):
        self.d = DownloadMonitor()

    def tearDown(self):
        pass

    def test_monitor_basic(self):
        self.d.remember(URIS[0], '0')
        self.d.remember(URIS[1], '1')
        self.d.remember(URIS[2], '2')
        self.assert_(self.d.check(URIS[0], '0'))
        self.assert_(self.d.check(URIS[1], '1'))
        self.assert_(self.d.check(URIS[2], '2'))
        self.assert_(not self.d.check(URIS[3], '3'))

    def test_monitor_dupe(self):
        self.d.remember(URIS[0], '0')
        self.d.remember(URIS[0], '1')
        self.d.remember(URIS[0], '2')
        self.assert_(self.d.check(URIS[0], '0'))
        self.assert_(self.d.check(URIS[0], '1'))
        self.assert_(self.d.check(URIS[0], '2'))
        self.assert_(not self.d.check(URIS[0], '3'))

    def test_monitor_overwrite(self):
        # doesn't really handle it...
        self.d.remember(URIS[0], '0')
        self.d.remember(URIS[1], '0')
        self.d.remember(URIS[2], '0')
        self.assert_(self.d.check(URIS[0], '0'))
        self.assert_(self.d.check(URIS[1], '0'))
        self.assert_(self.d.check(URIS[2], '0'))
        self.assert_(not self.d.check(URIS[1], '1'))
        self.assert_(not self.d.check(URIS[2], '2'))

class BaseCellMLBuilderTestCase(unittest.TestCase):

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.builder = CellMLBuilder(self.workdir, '')

    def tearDown(self):
        shutil.rmtree(self.workdir)

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

    def test_prepare_path(self):
        uri = URIS[0]  # beeler_reuter_1977_version01
        self.builder.uri = uri
        result = self.builder.prepare_path()
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

    def test_path_join(self):
        uri = URIS[0]  # beeler_reuter_1977_version01
        self.builder.uri = uri
        self.builder.prepare_path()
        p = self.builder.path_join('a')
        self.assertEqual(p, os.path.join(
            self.workdir, self.builder.citation, self.builder.version, 'a'))
        p = self.builder.path_join('a', 'b')
        self.assertEqual(p, os.path.join(
            self.workdir, self.builder.citation, self.builder.version, 
            'a', 'b'))

    def test_download(self):
        uri = 'http://www.example.com/notfound'
        notfound = os.path.join(self.workdir, 'notfound')
        self.builder.download(uri, notfound)
        self.assert_(not os.path.exists(notfound))
        self.assertEqual(self.builder.result['missing'], [uri])

        uri = 'http://www.example.com/'
        found = os.path.join(self.workdir, 'found')
        self.builder.download(uri, found)
        self.assert_(os.path.exists(found))

    def test_download_cellml_basic(self):
        uri = URIS[0]  # beeler_reuter_1977_version01
        self.builder.uri = uri
        self.builder.prepare_path()
        self.builder.download_cellml()
        self.assertEquals(self.builder.cellml_filename,
            os.path.join(self.workdir, 'beeler_reuter_1977', '01',
                'beeler_reuter_1977.cellml')
        )
        f = open(self.builder.cellml_filename).read()
        self.assert_('<model ' in f)
        self.assert_('cell_diagram.gif' in f)
        self.assert_('/cell_diagram.gif' not in f)

        self.assertEquals(self.builder.cellml_filename,
            os.path.join(self.workdir, 'beeler_reuter_1977', '01',
                'beeler_reuter_1977.cellml')
        )

        self.assert_(os.path.isfile(os.path.join(
            self.workdir, 'beeler_reuter_1977', '01', 'cell_diagram.gif'))
        )

    def test_download_cellml_variant(self):
        uri = URIS[8]  # bental_2006_version02_variant03
        self.builder.uri = uri
        self.builder.prepare_path()
        self.builder.download_cellml()
        f = open(self.builder.cellml_filename).read()
        self.assert_('<model ' in f)

    def test_download_cellml_cmeta_id(self):
        uri = URIS[17]  # noble_varghese_kohl_noble_1998
        self.builder.uri = uri
        self.builder.prepare_path()
        self.builder.download_cellml()
        f = open(self.builder.cellml_filename).read()
        self.assert_('cmeta:id="environment_time"' in f)

    def test_get_session_uri(self):
        uri = URIS[0]  # beeler_reuter_1977_version01
        self.builder.uri = uri
        session = self.builder.get_session_uri()
        self.assertEqual(session, None)

        uri = URIS[7]  # beeler_reuter_1977_version08
        self.builder.uri = uri
        session = self.builder.get_session_uri()
        self.assert_(session.startswith('http'))
        self.assert_(session.endswith(
            '/cellmlmodels/pcenv_session/beeler_reuter_1977/' \
            'beeler_reuter_1977_version08.session'
        ))

    def test_download_session(self):
        uri = URIS[7]  # beeler_reuter_1977_version08
        self.builder.uri = uri
        self.builder.prepare_path()
        self.builder.download_session()
        f = open(self.builder.result['session'])
        result = f.read()
        f.close()
        self.assert_(result.startswith('<?xml version='))
        self.assert_('<RDF:RDF' in result)
        self.assert_('/download' not in result)
        # the trailing cmeta id fragments remain
        self.assert_('"' + self.builder.result['cellml'] + '#' in result)
        self.assert_('.xul/' not in result)
        self.assert_('.cellml#environment_time' in result)

    def test_download_session_wrong(self):
        # tests session files that point to the _wrong_ model version
        uri = URIS[18]  # tentusscher_noble_noble_panfilov_2004_version04
        self.builder.uri = uri
        self.builder.prepare_path()
        self.builder.download_session()
        f = open(self.builder.result['session'])
        result = f.read()
        f.close()
        self.assert_(result.startswith('<?xml version='))
        self.assert_('<RDF:RDF' in result)
        self.assert_('/download' not in result)
        # the trailing cmeta id fragments remain
        self.assert_('"' + self.builder.result['cellml'] + '#' in result)
        self.assert_('.xul/' not in result)
        self.assert_('.cellml#environment_time' in result)

    def test_download_session_wrong2(self):
        # tests session files that point to the _wrong_ model version
        uri = URIS[16]  # noble_varghese_kohl_noble_1998_version06_variant01
        self.builder.uri = uri
        self.builder.prepare_path()
        self.builder.download_session()
        f = open(self.builder.result['session'])
        result = f.read()
        f.close()
        self.assert_(result.startswith('<?xml version='))
        self.assert_('<RDF:RDF' in result)
        self.assert_('/download' not in result)
        self.assert_('file://' not in result)
        # the trailing cmeta id fragments remain
        self.assert_('"' + self.builder.result['cellml'] + '#' in result)
        self.assert_('.xul/' not in result)
        self.assert_('.cellml#environment_time' in result)


class LiveBuilderTestCase(unittest.TestCase):
    """\
    Will use the full, live PMR instance.
    """

    # globals to reduce re-downloading stuff
    urilist = []

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        self.builddir = os.path.join(self.workdir, 'build')
        self.cbuilder = CellMLBuilder(self.workdir, '')
        self.builder = DirBuilder(self.builddir, [])

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_001_breakuri(self):
        LiveBuilderTestCase.urilist = uris = get_pmr_urilist(CELLML_FILE_LIST)
        output = [self.cbuilder.breakuri(os.path.basename(i)) for i in uris]
        self.assertEqual(len(uris), len(output))

    def test_002_run(self):
        self.builder.files = URIS
        result = self.builder._run()
        self.assertEqual(len(result), len(URIS))
        for i in result.values():
            self.assert_(not i['exists'])
        
        # miscellenous download data check
        # download file size check
        s = None
        t = None
        for i in xrange(1, 8):
            st = os.stat(os.path.join(self.builddir,
                'beeler_reuter_1977/0%d/cellml_rendering.gif' % i))
            fs = st.st_size
            mt = st.st_mtime
            if s is None:
                s = fs
                t = mt
            self.assertEqual(s, fs)
            self.assertEqual(t, mt)

        # XXX more assertions can be nice.


class WorkspaceBuilderTestCase(unittest.TestCase):
    """
    """

    def setUp(self):
        self.source = os.path.join(os.path.dirname(__file__), 'pmr_export')
        self.dest = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dest)

    def test_run(self):
        dest = os.path.join(self.dest, 'out')
        builder = WorkspaceBuilder(self.source, dest)
        builder.run()
        self.assert_(os.path.isdir(os.path.join(dest, 'model_0000')))
        self.assert_(os.path.isfile(os.path.join(dest, 'model_0000', 'data')))

        repodir = os.path.join(dest, 'model_0000')

        r = hg.repository(ui.ui(), repodir)
        cc = r.changelog.count()
        # XXX BUG
        # Mercurial thinks a file is the same if the datestamp and file
        # size (or just datestamp), there are no difference and so
        # the resulting changeset will overwrite the first one.
        self.assertEqual(cc, 2)


def test_suite():
    prepare_logger()
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DownloadMonitorTestCase))
    suite.addTest(unittest.makeSuite(BaseCellMLBuilderTestCase))
    suite.addTest(unittest.makeSuite(WorkspaceBuilderTestCase))
    suite.addTest(unittest.makeSuite(LiveBuilderTestCase))
    return suite

def cmd_suite():
    prepare_logger()
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DownloadMonitorTestCase))
    suite.addTest(unittest.makeSuite(BaseCellMLBuilderTestCase))
    suite.addTest(unittest.makeSuite(WorkspaceBuilderTestCase))
    if testlive:
        suite.addTest(unittest.makeSuite(LiveBuilderTestCase))
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

