import re
import os.path
import zope.component

import z3c.form.field
import z3c.form.form

from plone.z3cform import layout
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName

from pmr2.app.interfaces import *
from pmr2.app.content import *
from pmr2.app.browser import widget
from pmr2.app.browser import exposure

from interfaces import IPMRImportMap
from content import PMRImportMap


class PMR1MigratedView(layout.FormWrapper):
    """
    A hook for handling PMR1 uris.
    """

    form_instance = ViewPageTemplateFile('migrated.pt')

    def __call__(self):

        # search
        #for k, v in self.request['_pmr1']
        catalog = getToolByName(self.context, 'portal_catalog')
        self.related_exposures = catalog(
            pmr2_exposure_workspace=self.workspace)
        # no border in this case.
        self.request['disable_border'] = True
        return super(PMR1MigratedView, self).__call__()

    def label(self):
        return u'Model has been moved.'
