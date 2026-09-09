from django.test import SimpleTestCase


class LeaveModuleSmokeTests(SimpleTestCase):
    def test_module_imports(self):
        __import__("leave")
