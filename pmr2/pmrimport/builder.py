import re
import urllib
import os, os.path
import logging

CELLML_FILE_LIST = 'http://www.cellml.org/models/list_txt'


def get_pmr_urilist(filelisturi):
    """\
    Returns list of CellML files.
    """

    # XXX getPcenv_session_uri can be used for session uri
    # XXX likewise for curation, but curation flags need to be defined.
    return urllib.urlopen(filelisturi).read().split()


class DirBuilder(object):
    """\
    The class that will fetch the files from PMR.

    Each citation (name1_name2_name3_year) will be a directory, and each
    version/variant will also have its directory.  Files will be 
    downloaded along with all its dependencies.
    """

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

    def __init__(self, workdir, files=None, loglevel=logging.ERROR):
        self.workdir = workdir
        self.files = files
        self.filelisturi = CELLML_FILE_LIST

        self.prepare_logger(loglevel)

    def prepare_logger(self, loglevel):
        formatter = logging.Formatter('%(message)s')
        self.log = logging.getLogger('dirbuilder')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.log.setLevel(loglevel)

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

        # XXX maybe shutils does what we need here.

        d = os.path.join(self.workdir, *a)

        # assumes parent dir already exists.
        if not os.path.isdir(d):
            os.mkdir(d)

    def download(self, source, dest):
        """\
        Downloads data from source to destination.
        """
        s_fd = urllib.urlopen(source)
        d_fd = open(dest, 'w')
        d_fd.write(s_fd.read())

    def download_cellml(self, uri):
        self.log.debug('Downloading CellML from: %s', uri)
        dest = self.prepare_cellml_path(uri)
        self.download(uri + '/download', dest)
        self.log.debug('CellML saved to %s', dest)
        return dest

    def process(self, uri):
        # returns location of destination of files downloaded
        # XXX should be logging this
        cellml_dest = self.download_cellml(uri)
        return cellml_dest

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

    def _run(self):
        """\
        Starts the process.  Will write to filesystem.
        """

        # create working dir
        if os.path.isdir(self.workdir):
            raise ValueError('destination directory already exists')

        try:
            self.mkdir(self.workdir)
        except:
            raise ValueError('destination directory cannot be created')

        if not self.files:
            self.log.info('Getting file list from "%s"...' % self.filelisturi)
            self.files = get_pmr_urilist(self.filelisturi)
        self.log.info('Processing %d URIs...' % len(self.files))
        for i in self.files:
            self.process(i)
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
