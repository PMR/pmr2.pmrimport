import os.path
import zope.component

import z3c.form.field
import z3c.form.form

from plone.z3cform import layout

from pmr2.app.interfaces import *
from pmr2.app.content import *
from pmr2.app.browser import widget
from pmr2.app.browser import exposure

from interfaces import IPMRImportMap
from content import PMRImportMap
from constants import PMR_MAPPING_FILE


class PMR2ImportForm(z3c.form.form.AddForm):
    """\
    PMR2ImportForm Bulk Add Form
    """

    @property
    def fields(self):
        fields = z3c.form.field.Fields(IWorkspaceBulkAdd)
        fields['workspace_list'].widgetFactory[
            z3c.form.interfaces.INPUT_MODE] = widget.TextAreaWidgetFactory
        return fields

    result_base = """\
      <dt>%s</dt>
      <dd>%d</dd>
    """

    failure_base = """
      <dt>%s</dt>
      <dd>
      <ul>
      %s
      </ul>
      </dd>
    """

    def completed(self):
        result = ['<p>The results of the bulk import:</p>', '<dl>']
        if self.created:
            result.append(self.result_base % ('Success', self.created))
        if self.existed:
            result.append(self.result_base % ('Existed', self.existed))
        if self.exposed:
            result.append(self.result_base % ('Exposure Made', self.existed))

        if self.norepo:
            result.append(self.failure_base % ('Mercurial Repo Not Found',
            '\n'.join(['<li>%s</li>' % i for i in self.norepo]))
        )
        if self.noexp:
            result.append(self.failure_base % ('Exposure Creation Failed',
            '\n'.join(['<li>%s</li>' % i for i in self.noexp]))
        )
        if self.failed:
            result.append(self.failure_base % ('Other Failure',
            '\n'.join(['<li>%s</li>' % i for i in self.failed]))
        )
        result.append('</dl>')
        return '\n'.join(result)

    def createAndAdd(self, data):
        """
        This assumes workspace and exposure exists and are the respective
        containers of a default/fresh PMR2 instance.
        """

        # XXX validation make sure this thing does not exist.
        # self.context[PMR_MAPPING_FILE]

        def build_workspace(id_):
            # makes the workspace object if it does not currently exist
            # gets one if it does.
            if id_ in workspace_root:
                self.existed += 1
                return True
            else:
                try:
                    obj = Workspace(id_, **data)
                    zope.event.notify(
                        zope.lifecycleevent.ObjectCreatedEvent(obj))
                    workspace_root[id_] = obj
                    obj = workspace_root[id_]
                    obj.title = id_.replace('_', ', ').title()
                    obj.notifyWorkflowCreated()
                    obj.reindexObject()
                    self.created += 1
                    return True
                except:
                    # log stacktrace?
                    self.failed.append(id_)
                    return None

        def build_exposure(id_):
            # create exposure root object using the form for consistency.
            obj = workspace_root[id_]
            try:
                storage = zope.component.queryMultiAdapter((obj, ), 
                    name='PMR2Storage')
                manifest = storage.manifest(None, '').next()
                filenames = [i['file'] for i in manifest['fentries']()
                                     if i['file'].endswith('.cellml')]
                if manifest['node'] in curmap:
                    clist = [i.split(':') for i in 
                                 curmap[manifest['node']].split(',') if i]
                    curation = dict([(i[0], [i[1]]) for i in clist])
                else:
                    curation = {}
                # exposure obj
                # again, we use revision id, they shouldn't collide.
                fdata = {
                    'title': obj.title,
                    'workspace': unicode(id_),
                    'commit_id': unicode(manifest['node']),
                    'curation': curation,
                }
                # XXX curation not implemented here or at the form!
                form = exposure.ExposureAddForm(exposure_root, None)
                form.createAndAdd(fdata)
                expid = fdata['id']
                exp_obj = exposure_root[expid]

                # meta exposure
                for filename in filenames:
                    fdata = {
                        'filename': unicode(filename),
                        'exposure_factory': u'ExposurePMR1MetadocFactory',
                    }
                    form = exposure.ExposureMetadocGenForm(exp_obj, None)
                    form.createAndAdd(fdata)
            except Exception, e:
                self.noexp.append('%s: %s' % (id_, e))

        mapping_file = os.path.join(self.context.workspace.get_path(), 
                                    PMR_MAPPING_FILE)
        mf = open(mapping_file)
        rawmap = mf.read()
        mf.close()
        map = {}
        curmap = {}
        for entry in rawmap.splitlines():
            old, current_fn, rev, curation = entry.split(' ')
            map[old] = (current_fn, rev, curation)
            # potentially be replaced by different data source, but if
            # curators gave all models from same rev consistent rating
            # also assuming revision id don't happen to collide
            curmap[rev] = unicode(curation)

        # adapt PMR2 into the ImportMap object, and assign the map 
        # attribute to it.
        ctxobj = zope.component.queryAdapter(self.context, name='PMRImportMap')
        ctxobj.pmrimport_map = map

        self.created = self.existed = self.exposed = 0
        self.failed = []
        self.norepo = []
        self.noexp = []

        workspace_root = self.context.workspace
        exposure_root = self.context.exposure

        workspaces = data['workspace_list'].splitlines()

        # List of Mercurial repos in the workspace root.
        valid_hg = [i[0] for i in workspace_root.get_repository_list()]

        for id_ in workspaces:

            # some validation on input id.
            if not id_:
                # nothing.
                continue
            if id_ not in valid_hg:
                # Only repo not found are reported as failures.
                self.norepo.append(id_)
                continue

            # unicode encoding needed here?
            id_ = str(id_)  # id_.encode('utf8')
            if not build_workspace(id_):
                # we can't do anything without a workspace.
                continue

            build_exposure(id_)

        # marking this as done.
        self._finishedAdd = True

    def nextURL(self):
        """\
        Go back to context.
        """

        return self.context.absolute_url()

    def render(self):
        if self._finishedAdd:
            return self.completed()
        return super(PMR2ImportForm, self).render()

PMR2ImportFormView = layout.wrap_form(
    PMR2ImportForm, label="PMR2 Bulk Importer")
