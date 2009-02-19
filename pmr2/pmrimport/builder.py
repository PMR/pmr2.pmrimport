import re
import urllib, urllib2
import os, os.path
import logging
from cStringIO import StringIO

import lxml.etree

CELLML_FILE_LIST = 'http://www.cellml.org/models/list_txt'
CELLML_NSMAP = {
    'tmpdoc': 'http://cellml.org/tmp-documentation',
    'pcenv': 'http://www.cellml.org/tools/pcenv/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}
PCENV_SESSION_FRAG = '/getPcenv_session_uri'
BAD_FRAG = [
    'attachment_download',
]


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
                data.write(d_fd, encoding='utf-8', xml_declaration=True)
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
                orig = open(dest).read()
                if data == orig:
                    # nothing else to do
                    return None
                self.log.warning('%s is different from %s, which exists!',
                    source, dest)
                self.result['exists'].append((dest, source))
                return None
            d_fd = open(dest, 'w')
            write(data)
            d_fd.close()

    def get_baseuri(self, uri):
        frags = uri.split('/')
        #for b in BAD_FRAG:
        #    try:
        #        frags = frags[:frags.index(b)]
        #    except:
        #        pass
        return frags.pop()

    @property
    def cellml_download_uri(self):
        return self.uri + '/download'

    @property
    def cellml_filename(self):
        return self.defaultname + '.cellml'

    @property
    def session_filename(self):
        return self.defaultname + '.session.xml'

    @property
    def xul_filename(self):
        return self.defaultname + '.xul'

    def download_cellml(self):
        self.log.debug('.d/l cellml: %s', self.uri)
        dest = self.result['cellml']
        self.download(self.cellml_download_uri, dest, self.process_cellml)
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
                i.attrib['fileref'] = self.get_baseuri(i.attrib['fileref'])

    def download_images(self, images):
        """\
        Downloads the images and returns the list of uri fragments.
        """
        for i in images:
            uri = urllib.basejoin(self.uri, i)
            dest = self.path_join(self.get_baseuri(uri))
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
        self.baseuri = self.get_baseuri(self.uri)
        self.breakuri(self.baseuri)

        self.mkdir(self.citation)
        self.mkdir(self.citation, self.version)
        self.defaultname = self.path_join(
            self.re_clean_name.sub('\\1', self.baseuri))
        cellml_path = self.cellml_filename
        self.result['cellml'] = cellml_path
        return cellml_path

    def process_session(self, data):
        # XXX quick replace
        data = data.replace(self.cellml_download_uri, self.cellml_filename)

        dom = lxml.etree.parse(StringIO(data))
        xulpath = dom.xpath('.//rdf:Description[@pcenv:externalurl]',
            namespaces=CELLML_NSMAP)
        # get and update the XUL file
        for en in xulpath:
            self.download_xul(en)
        return dom

    def download_session(self):
        session_uri = self.get_session_uri()
        if not session_uri:
            return
        self.log.debug('..d/l session: %s', session_uri)
        self.result['session'] = self.session_filename
        self.download(session_uri, self.session_filename, self.process_session)
        self.log.debug('..w session: %s', self.session_filename)

    def download_xul(self, node):
        # Since this is the end step, going to combine the processing
        # of the URI of the node within here also.
        xul_uri = node.attrib[
            '{http://www.cellml.org/tools/pcenv/}externalurl']
        self.log.debug('..d/l xul: %s', xul_uri)
        self.download(xul_uri, self.xul_filename)
        self.log.debug('..w xul: %s', self.session_filename)
        # correction
        node.attrib['{http://www.cellml.org/tools/pcenv/}externalurl'] = \
            self.xul_filename

    def get_session_uri(self):
        # not making this a property because this fetches an external
        # uri, but I supposed results can be cached... but in the
        # interest of KISS (for me anyway)...
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
        return self.result
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
        self.summary = {}

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
        else:
            self.log.info('File list already defined')
        self.log.info('Processing %d URIs...' % len(self.files))
        for i in self.files:
            processor = CellMLBuilder(self.workdir, i)
            result = processor.run()
            self.summary[i] = result
            self.log.info('Processed: %s', i)
        return self.summary

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
