from zope import interface
from zope.schema import fieldproperty
from interfaces import IPMRImportMap
#from persistent import Persistent
from Products.Archetypes.atapi import BaseContent

from pmr2.app.interfaces import *
from pmr2.app.mixin import TraversalCatchAll


#class PMRImportMap(Persistent):
class PMRImportMap(BaseContent):
    """\
    The PMR Import map implementation.
    """

    interface.implements(IPMRImportMap)
    map = fieldproperty.FieldProperty(IPMRImportMap['map'])

    def find_uri(self, uri):
        if uri not in self.map:
            return None

        # XXX since workspace name is not saved but derived from 
        # original filename.
        workspace = s[:s.index('_version')]
        rev, file = self.map[uri]
        return (workspace, rev, file)
