import zope.interface
import zope.schema

class IPMRImportMap(zope.interface.Interface):
    """\
    Maps between the two thing,
    """

    map = zope.schema.Dict(
        title=u'Model Map',
        description=u'The dictionary of mappings between PMR and PMR2.',
    )

    def find_uri(uri):
        """\
        Returns the new URI to the model, given the old model name.
        """
