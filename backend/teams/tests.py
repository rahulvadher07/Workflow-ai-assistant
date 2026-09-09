from django.test import SimpleTestCase


class TeamsModuleSmokeTests(SimpleTestCase):
    def test_module_imports(self):
        __import__("teams")
