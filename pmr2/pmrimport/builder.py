import re
import urllib, urllib2
import os, os.path
import logging
from cStringIO import StringIO

import lxml.etree

CELLML_FILE_LIST = 'http://www.cellml.org/models/list_txt'


def get_pmr_urilist(filelisturi):
    """\
    Returns list of CellML files.
    """

    # XXX getPcenv_session_uri can be used for session uri
    # XXX likewise for curation, but curation flags need to be defined.
    return urllib2.urlopen(filelisturi).read().split()

def prepare_logger(loglevel):
    formatter = logging.Formatter('%(message)s')
    logger = logging.getLogger('dirbuilder')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(loglevel)


class CellMLBuilder(object):

    # TODO
    # * correction of image links to relative paths within the same dir
    #   within tmpdoc.
    # * download PCEnv sessions
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
        self.result = {}

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
        """

        d_fd = open(dest, 'w')

        try:
            s_fd = urllib2.urlopen(source)
        except urllib2.HTTPError, e:
            self.log.warning('HTTP %s on %s', e.code, source)
            return

        data = s_fd.read()

        if processor:
            data = processor(data)
        d_fd.write(data)

    def download_cellml(self):
        self.log.debug('.d/l cellml: %s', self.uri)
        dest = self.prepare_cellml_path()
        self.download(self.uri + '/download', dest, self.process_cellml)
        self.log.debug('.w cellml: %s', dest)
        self.result['dest'] = dest

    def process_cellml(self, data):
        dom = lxml.etree.parse(StringIO(data))
        images = dom.xpath('.//tmpdoc:imagedata/@fileref', 
            namespaces={'tmpdoc': 'http://cellml.org/tmp-documentation'})
        self.download_images(images)
        return data

    def download_images(self, images):
        """\
        Downloads the images and returns the list of uri fragments.
        """
        for i in images:
            uri = urllib.basejoin(self.uri, i)
            dest = self.build_path(os.path.basename(uri))
            self.log.debug('..d/l image: %s', uri)
            self.download(uri, dest)
            self.log.debug('..w image: %s', dest)
        return images

    def build_path(self, *path):
        return os.path.join(self.workdir, self.citation, self.version, *path)

    def prepare_cellml_path(self):
        """\
        This creates the base directory structure and returns the
        location of the destination of the CellML file.
        """

        # preparation
        self.baseuri = os.path.basename(self.uri)
        self.breakuri(self.baseuri)

        self.mkdir(self.citation)
        self.mkdir(self.citation, self.version)
        cellml_path = self.build_path(
            self.re_clean_name.sub('\\1.cellml', self.baseuri)
        )
        return cellml_path

    def get_result(self, key):
        return self.result.get(key, None)

    def run(self):
        """\
        Processes the CellML URI in here.
        """

        self.download_cellml()
        # self.download_session()
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
