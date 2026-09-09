import json
import re
import unittest
from pathlib import Path


class RuleCatalogArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.catalog = json.loads((cls.root / "agent_rules.json").read_text(encoding="utf-8"))
        cls.orchestrator = (cls.root / "orchestrator.py").read_text(encoding="utf-8")

    def test_global_confirmation_policy_is_single_source(self):
        self.assertTrue(self.catalog["confirmation_policy"]["requires_active_pending_preview"])
        self.assertTrue(self.catalog["confirmation_policy"]["requires_same_authenticated_user"])
        self.assertTrue(self.catalog["confirmation_policy"]["requires_immediate_next_turn"])
        self.assertEqual([], [r["id"] for r in self.catalog["rules"] if r.get("confirmation_phrases")])

    def test_deterministic_rules_have_convention_based_handlers(self):
        keys = {
            r.get("router_key") for r in self.catalog["rules"]
            if r.get("execution_mode") == "DETERMINISTIC" and r.get("router_key")
        }
        self.assertTrue(keys)
        missing = [key for key in keys if not re.search(rf"def _route_{re.escape(key)}\(", self.orchestrator)]
        self.assertEqual([], missing)

    def test_routing_contract_is_declared(self):
        contract = self.catalog.get("routing_contract") or {}
        self.assertEqual("confirmation_policy", contract.get("confirmation_policy_reference"))
        self.assertEqual(["SPECIFIC_EMPLOYEE", "TEAM", "PERSONAL", "COMPANY_WIDE"], contract.get("scope_precedence"))


if __name__ == "__main__":
    unittest.main()
