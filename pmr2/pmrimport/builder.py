import re
import urllib
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
    return urllib.urlopen(filelisturi).read().split()

def prepare_logger(loglevel):
    formatter = logging.Formatter('%(message)s')
    logger = logging.getLogger('dirbuilder')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(loglevel)


class CellMLBuilder(object):

    # TODO
    # * extract images from tmpdoc
    #   - correction of image links to relative paths within the same dir
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
            x, citation, version, variant, part, x = \
                self.re_breakuri.split(baseuri)
        except ValueError:
            raise ValueError("'%s' is an invalid base uri" % baseuri)
        return citation, version, variant, part

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

        s_fd = urllib.urlopen(source)
        d_fd = open(dest, 'w')
        data = s_fd.read()
        result = {}
        if processor:
            data, result = processor(data)
        d_fd.write(data)
        return result

    def download_cellml(self, uri):
        self.log.debug('Downloading CellML from: %s', uri)
        dest = self.prepare_cellml_path(uri)
        result = self.download(uri + '/download', dest, self.process_cellml)
        self.log.debug('CellML saved to %s', dest)
        result['dest'] = dest
        return result

    def process_cellml(self, data):
        result = {}
        dom = lxml.etree.parse(StringIO(data))
        images = dom.xpath('.//tmpdoc:imagedata/@fileref', 
            namespaces={'tmpdoc': 'http://cellml.org/tmp-documentation'})
        return data, result

    def prepare_cellml_path(self, uri):
        """\
        This creates the base directory structure and returns the
        location of the destination of the CellML file.
        """

        baseuri = os.path.basename(uri)
        citation, version, variant, part = self.breakuri(baseuri)
        self.mkdir(citation)
        self.mkdir(citation, version)
        cellml_path = os.path.join(
            self.workdir, citation, version,
            self.re_clean_name.sub('\\1.cellml', baseuri)
        )
        return cellml_path

    def run(self):
        # returns location of destination of files downloaded
        # XXX should be logging this
        result = self.download_cellml(self.uri)
        return result


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
