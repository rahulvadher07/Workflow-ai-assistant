from django.test import SimpleTestCase


class WorkspaceModuleSmokeTests(SimpleTestCase):
    def test_module_imports(self):
        __import__("workspace")
