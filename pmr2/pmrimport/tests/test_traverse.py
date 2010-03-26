from unittest import TestCase, TestSuite, makeSuite
from Acquisition import Implicit
import zope.interface
import zope.component
import zope.interface
from zope.interface.verify import verifyClass
from zope.publisher.interfaces import IPublishTraverse
from paste.httpexceptions import HTTPNotFound, HTTPFound

from pmr2.app.interfaces import *
from pmr2.app.tests.base import TestRequest

import pmr2.pmrimport
from pmr2.pmrimport.traverse import PMR1Traverser
from pmr2.pmrimport.interfaces import *
from pmr2.pmrimport.browser import PMR1MigratedView


class MockContext(Implicit):
    def absolute_url(self):
        return 'http://nohost/plone'

mock_context = MockContext()

class MockSettings(object):
    zope.interface.implements(IPMR2GlobalSettings)
    default_workspace_subpath = u'workspace'

class MockMap(object):
    pmrimport_map = {
        'model_2000_version01': (
            'model_2000',
            '12345',
        ),
        'model_2001_version01': (
            'model_2001_a',
            '13579',
        ),
        'model_2001_version02': (
            'model_2001_b',
            '13579',
        ),
        'model_2001_version03': (
            'model_2001_c',
            '13579',
        ),
    }
    def __init__(self, *a, **kw):
        pass


class TestTraverser(TestCase):

    def setUp(self):
        def traverse(self, request, name):
            raise AttributeError

        PMR1Traverser.o_defaultTraverse = PMR1Traverser.defaultTraverse
        PMR1Traverser.defaultTraverse = traverse

        self.settings = MockSettings()
        self.sm = zope.component.getSiteManager()
        self.sm.registerUtility(self.settings, IPMR2GlobalSettings)

        zope.component.provideAdapter(MockMap, (MockContext,), IPMRImportMap, 
                                      name='PMRImportMap',)
        zope.component.provideAdapter(PMR1MigratedView, 
                                      (MockContext, TestRequest,), 
                                      zope.interface.Interface, name='pmr1',)

    def tearDown(self):
        self.sm.unregisterUtility(self.settings, IPMR2GlobalSettings)
        PMR1Traverser.defaultTraverse = PMR1Traverser.o_defaultTraverse 
        del PMR1Traverser.o_defaultTraverse 

    def testInterface(self):
        self.failUnless(verifyClass(IPublishTraverse, PMR1Traverser))

    def testPMR1Traverser_001_badlink(self):
        request = TestRequest(TraversalRequestNameStack=[])
        traverser = PMR1Traverser(mock_context, request)
        self.assertRaises(HTTPNotFound,
            traverser.publishTraverse, request, 'model_2000')

    def testPMR1Traverser_002_pmr_model(self):
        request = TestRequest(TraversalRequestNameStack=['pmr_model'])
        traverser = PMR1Traverser(mock_context, request)
        traverser.publishTraverse(request, 'model_2000_version01')
        self.assertEqual(request.response.getHeader('location'),
            'http://nohost/plone/workspace/model_2000/@@rawfile/12345'
            '/model_2000.cellml')

    def testPMR1Traverser_003_download(self):
        # similar to above test, but we also test redirection to model
        # that had its file renamed due to version flattening into 
        # variants.
        request = TestRequest(TraversalRequestNameStack=['download'])
        traverser = PMR1Traverser(mock_context, request)
        traverser.publishTraverse(request, 'model_2001_version03')
        self.assertEqual(request.response.getHeader('location'),
            'http://nohost/plone/workspace/model_2001/@@rawfile/13579'
            '/model_2001_c.cellml')

    def testPMR1Traverser_010_nostack(self):
        request = TestRequest(TraversalRequestNameStack=[])
        traverser = PMR1Traverser(mock_context, request)
        result = traverser.publishTraverse(request, 'model_2000_version01')
        self.failUnless(isinstance(result, PMR1MigratedView))
        self.assertEqual(result.workspace, 'model_2000')
        self.assertEqual(result.model_name, 'model_2000_version01')
        self.assertEqual(result.commit_id, '12345')
        self.assertEqual(result.workspace_uri,
            'http://nohost/plone/workspace/model_2000/@@file/12345')

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestTraverser))
    return suite

