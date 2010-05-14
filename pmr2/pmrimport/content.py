from zope import interface
from zope import component
from zope.schema import fieldproperty
from zope.annotation import factory
from zope.annotation.interfaces import IAttributeAnnotatable
from persistent import Persistent

from pmr2.app.content.interfaces import IPMR2

from interfaces import IPMRImportMap


class PMRImportMap(Persistent):
    """\
    The PMR Import map implementation.
    """

    interface.implements(IPMRImportMap)
    component.adapts(IAttributeAnnotatable)
    pmrimport_map = fieldproperty.FieldProperty(IPMRImportMap['pmrimport_map'])

    def find_uri(self, uri):
        if uri not in self.pmrimport_map:
            return None

        # XXX since workspace name is not saved but derived from 
        # original filename.
        workspace = s[:s.index('_version')]
        rev, file = self.pmrimport_map[uri]
        return (workspace, rev, file)

PMRImportMapFactory = factory(PMRImportMap)
