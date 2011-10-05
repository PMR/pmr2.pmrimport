import re
import os.path
import zope.component

import z3c.form.field
import z3c.form.form

from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName

from pmr2.app.interfaces import *
from pmr2.app.content import *
from pmr2.app.browser import widget
from pmr2.app.exposure import browser as exposure

from interfaces import IPMRImportMap
from content import PMRImportMap


class PMR1MigratedView(BrowserPage):
    """
    A view with information about the PMR1 to PMR2 migration.
    """

    template = ViewPageTemplateFile('migrated.pt')

    # these are set by the traverser that's part of this module.
    workspace = None
    model_name = None
    commit_id = None
    workspace_uri = None
    workspace_rev_uri = None

    def __call__(self):

        # This view is not meant to be accessed directly by a client.
        # Redirect to context's default view if none of the values above
        # are set (so don't set this as the default view).
        if self.workspace is None:
            return self.request.response.redirect(self.context.absolute_url())

        catalog = getToolByName(self.context, 'portal_catalog')

        # search the catalog for the exposure page for this version of
        # the model.
        exposure = catalog(
            review_state='published',
            pmr2_exposure_workspace=self.workspace,
            pmr2_exposure_commit_id=self.commit_id,
        )
        if exposure:
            # join
            target = '%s/%s.cellml/view' % (
                exposure[0].getURL(), self.migration_info[0])
            # would be nice if we can set an informative status message
            # about redirection due to migration of PMR1 to PMR2.
            return self.request.response.redirect(target)

        # looks like there isn't an exposure page for this version, so
        # we find exposure pages from this workspace.
        self.related_exposures = catalog(
            review_state='published',
            pmr2_exposure_workspace=self.workspace,
            )
        # no border in this case.
        self.request['disable_border'] = True
        return self.template()
