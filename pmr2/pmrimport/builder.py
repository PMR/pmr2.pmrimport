import re
import urllib
import os, os.path

CELLML_FILE_LIST = 'http://www.cellml.org/models/list_txt'


def get_pmr_urilist():
    """\
    Returns list of CellML files.
    """

    # XXX getPcenv_session_uri can be used for session uri
    # XXX likewise for curation, but curation flags need to be defined.
    return urllib.urlopen(CELLML_FILE_LIST).read().split()


class DirBuilder(object):
    """\
    The class that will fetch the files from PMR.

    Each citation (name1_name2_name3_year) will be a directory, and each
    version/variant will also have its directory.  Files will be 
    downloaded along with all its dependencies.
    """

    re_breakuri = re.compile(
        '^([a-zA-Z\-_]*(?:_[0-9]{4})?)_' \
        '(?:version([0-9]{2}))' \
        '(?:_(variant[0-9]{2}))?' \
        '(?:_(part[0-9]{2}))?$'
    )

    def __init__(self, workdir, files=None):
        self.workdir = workdir
        self.files = files

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

    def mkdir(self, citation=None):
        """\
        Creates a directory within the working directory.  If directory
        is already created nothing is done.
        """

        if citation:
            d = os.path.join(self.workdir, citation)
        else:
            d = self.workdir

        if not os.path.isdir(d):
            os.mkdir(d)

    def process(self, uri):
        baseuri = os.path.basename(uri)
        citation, version, variant, part = self.breakuri(baseuri)

    def run(self):
        """\
        Starts the process.  Will write to filesystem.
        """

        # create working dir
        self.mkdir()
        for i in self.files:
            self.process(i)


class WorkspaceBuilder(object):
    """\
    The class that will faciliate the construction of the workspace
    directory structure.  Uses the abo
    """
