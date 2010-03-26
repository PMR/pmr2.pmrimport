import zope.interface
import zope.schema

class IPMRImportMap(zope.interface.Interface):
    """\
    Maps between the two thing,
    """

    pmrimport_map = zope.schema.Dict(
        title=u'PMR Import Model Map',
        description=u'The dictionary of mappings between PMR and PMR2.',
    )

    def find_uri(uri):
        """\
        Returns the new URI to the model, given the old model name.
        """


class IPMR1(zope.interface.Interface):
    """\
    Marker interface for traversing.
    """
