import zope.component
from zope.publisher.interfaces import IRequest, NotFound
from ZPublisher.BaseRequest import DefaultPublishTraverse

from pmr2.app.settings.interfaces import IPMR2GlobalSettings
from pmr2.pmrimport.interfaces import IPMR1


class PMR1Traverser(DefaultPublishTraverse):
    """\
    Traverser that adapts the PMR1 marker interface to enable 
    redirection of saved PMR1 URIs to models to the correct counterpart
    within PMR2.  The marker interface should be annotated to ISiteRoot.
    """

    zope.component.adapts(IPMR1, IRequest)

    def defaultTraverse(self, request, name):
        return super(PMR1Traverser, self).publishTraverse(request, name)

    def publishTraverse(self, request, name):
        try:
            return self.defaultTraverse(request, name)
        except (AttributeError, KeyError):
            pass

        settings = zope.component.queryUtility(IPMR2GlobalSettings)
        map = zope.component.queryAdapter(self.context, name='PMRImportMap')
        if not settings:
            # we could assume the workspace_root is 'workspace', but...
            raise NotFound(self.context, name)

        if not map or name not in map.pmrimport_map:
            raise NotFound(self.context, name)

        workspace_root = settings.default_workspace_subpath
        info = map.pmrimport_map[name]
        trail = request['TraversalRequestNameStack']
        request['TraversalRequestNameStack'] = []

        # have to compute values related to the workspace from the 
        # requested id as it was just different (and not stored).
        workspace_id = name[:name.find('_version')]

        workspace_pfrags = (
            self.context.getPhysicalPath() + 
            (workspace_root,) +
            (workspace_id,)
        )

        # the new full workspace path is expected in the new catalog
        # search that will be done by the view
        workspace = '/'.join(workspace_pfrags)

        rev = info[1]
        name = name

        workspace_uri = '/'.join([
            self.context.absolute_url(), 
            workspace_root,
            workspace_id,
        ])

        workspace_rev_uri = '/'.join([
            self.context.absolute_url(), 
            workspace_root,
            workspace_id,
            '@@%s',
            rev,
        ])

        if trail and trail[0] in ('download', 'pmr_model'):
            # we redirect to the original CellML file that should now
            # be in a workspace.
            fn = info[0] + '.cellml'
            uri = '/'.join((workspace_rev_uri, fn,)) % 'rawfile'
            return request.response.redirect(uri)

        view = zope.component.getMultiAdapter((self.context, request), 
                                              name='pmr1')
        view.workspace = workspace
        view.model_name = name
        view.commit_id = rev
        view.migration_info = info
        view.workspace_uri = workspace_uri
        view.workspace_rev_uri = workspace_rev_uri % 'file'
        return view
