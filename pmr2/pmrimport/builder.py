import re
import urllib, urllib2
import os, os.path
import logging
from cStringIO import StringIO

import lxml.etree

CELLML_FILE_LIST = 'http://www.cellml.org/models/list_txt'
CELLML_NSMAP = {
    'tmpdoc': 'http://cellml.org/tmp-documentation',
}
PCENV_SESSION_FRAG = '/getPcenv_session_uri'


def get_pmr_urilist(filelisturi):
    """\
    Returns list of CellML files.
    """

    return urllib2.urlopen(filelisturi).read().split()

def prepare_logger(loglevel=logging.ERROR):
    formatter = logging.Formatter('%(message)s')
    logger = logging.getLogger('dirbuilder')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(loglevel)


class CellMLBuilder(object):

    # TODO
    # * correction of image file names to remove /download, /view and 
    #   the like
    # * PCEnv session links
    #   - correct session URIs to local relative links
    #   - download XUL files and update reference to local

    re_breakuri = re.compile(
        '^([a-zA-Z\-_]*(?:_[0-9]{4})?)_' \
        '(?:version([0-9]{2}))' \
        '(?:_(variant[0-9]{2}))?' \
        '(?:_(part[0-9]{2}))?$'
    )

    re_clean_name = re.compile('_version[0-9]{2}(.*)$')

    def __init__(self, workdir, uri):
        self.uri = uri
        self.workdir = workdir
        self.log = logging.getLogger('dirbuilder')
        self.result = {
            'cellml': None,
            'images': [],
            'session': None,
            'missing': [],
            'exists': [],
        }

    def breakuri(self, baseuri):
        """\
        Breaks the Base URI down to the required fragments.
        """

        try:
            x, self.citation, self.version, self.variant, self.part, x = \
                self.re_breakuri.split(baseuri)
        except ValueError:
            raise ValueError("'%s' is an invalid base uri" % baseuri)
        return self.citation, self.version, self.variant, self.part

    def mkdir(self, *a):
        """\
        Creates a directory within the working directory.  If directory
        is already created nothing is done.
        """

        d = os.path.join(self.workdir, *a)
        # assumes parent dir already exists.
        if not os.path.isdir(d):
            os.mkdir(d)

    def download(self, source, dest, processor=None):
        """\
        Downloads data from source to destination.

        source -
            uri.
        dest -
            file name of destination.
            alternately, a file-like object may be supplied.
        processor -
            function or method to process results.
        """

        def write(data):
            # if data implements write (i.e. dom), use that instead.
            if hasattr(data, 'write'):
                data.write(d_fd)
            else:
                d_fd.write(data)

        try:
            s_fd = urllib2.urlopen(source)
        except urllib2.HTTPError, e:
            if e.code >= 400:
                self.result['missing'].append(source)
                self.log.warning('HTTP %d on %s', e.code, source)
            return None

        data = s_fd.read()
        s_fd.close()

        if processor:
            data = processor(data)

        if hasattr(dest, 'write'):
            # assume a valid stream object
            d_fd = dest
            write(data)
            # since destination is opened outside of this method, we
            # don't close it in here.
        else:
            if os.path.exists(dest):
                self.log.warning('%s already exists!', dest)
                self.result['exists'].append((dest, source))
                return None
            d_fd = open(dest, 'w')
            write(data)
            d_fd.close()

    def download_cellml(self):
        self.log.debug('.d/l cellml: %s', self.uri)
        dest = self.result['cellml']
        self.download(self.uri + '/download', dest, self.process_cellml)
        self.log.debug('.w cellml: %s', dest)

    def process_cellml(self, data):
        dom = lxml.etree.parse(StringIO(data))
        images = dom.xpath('.//tmpdoc:imagedata/@fileref',
            namespaces=CELLML_NSMAP)
        self.download_images(images)
        # update the dom nodes

        self.process_cellml_dom(dom)
        return dom

    def process_cellml_dom(self, dom):
        """\
        Updates the DOM to have correct relative links.
        """

        imagedata = dom.xpath('.//tmpdoc:imagedata',
            namespaces=CELLML_NSMAP)
        for i in imagedata:
            if 'fileref' in i.attrib:
                i.attrib['fileref'] = os.path.basename(i.attrib['fileref'])

    def download_images(self, images):
        """\
        Downloads the images and returns the list of uri fragments.
        """
        for i in images:
            uri = urllib.basejoin(self.uri, i)
            dest = self.path_join(os.path.basename(uri))
            self.log.debug('..d/l image: %s', uri)
            self.download(uri, dest)
            self.log.debug('..w image: %s', dest)
            self.result['images'].append(dest)
        return images

    def path_join(self, *path):
        return os.path.join(self.workdir, self.citation, self.version, *path)

    def prepare_path(self):
        """\
        This creates the base directory structure and returns the
        location of the destination of the CellML file.
        """

        # preparation
        self.baseuri = os.path.basename(self.uri)
        self.breakuri(self.baseuri)

        self.mkdir(self.citation)
        self.mkdir(self.citation, self.version)
        cellml_path = self.path_join(
            self.re_clean_name.sub('\\1.cellml', self.baseuri)
        )
        self.result['cellml'] = cellml_path
        return cellml_path

    def download_session(self):
        session_uri = self.get_session_uri()
        if not session_uri:
            return
        self.log.debug('..d/l session: %s', session_uri)
        session_file = self.path_join(os.path.basename(session_uri))
        self.result['session'] = session_file
        self.download(session_uri, session_file)

    def get_session_uri(self):
        session = StringIO()
        self.download(self.uri + PCENV_SESSION_FRAG, session)
        session = session.getvalue() or None
        if session:
            session = urllib.basejoin(self.uri, session)
        return session

    def get_result(self, key):
        return self.result.get(key, None)

    def run(self):
        """\
        Processes the CellML URI in here.
        """

        self.prepare_path()
        self.download_cellml()
        self.download_session()
        # self.get_curation()


class DirBuilder(object):
    """\
    The class that will fetch the files from PMR.

    Each citation (name1_name2_name3_year) will be a directory, and each
    version/variant will also have its directory.  Files will be 
    downloaded along with all its dependencies.
    """

    def __init__(self, workdir, files=None, loglevel=logging.ERROR):
        self.workdir = workdir
        self.files = files
        self.filelisturi = CELLML_FILE_LIST
        prepare_logger(loglevel)
        self.log = logging.getLogger('dirbuilder')

    def _run(self):
        """\
        Starts the process.  Will write to filesystem.
        """

        # create working dir
        if os.path.isdir(self.workdir):
            raise ValueError('destination directory already exists')

        try:
            os.mkdir(self.workdir)
        except OSError:
            raise ValueError('destination directory cannot be created')

        if not self.files:
            self.log.info('Getting file list from "%s"...' % self.filelisturi)
            self.files = get_pmr_urilist(self.filelisturi)
        self.log.info('Processing %d URIs...' % len(self.files))
        for i in self.files:
            processor = CellMLBuilder(self.workdir, i)
            result = processor.run()
            self.log.info('Processed: %s', i)

    def run(self):
        try:
            self._run()
        except ValueError, e:
            self.log.error('ERROR: %s' % e)
            return 2
        except KeyboardInterrupt, e:
            self.log.error('user aborted!')
            return 255
        return 0


class WorkspaceBuilder(object):
    """\
    The class that will faciliate the construction of the workspace
    directory structure.  Uses the abo
    """
