import test from "node:test";
import assert from "node:assert/strict";
import { normalizeResource, resourcesMatch } from "../src/services/dataChangeBus.js";

test("normalizeResource maps aliases consistently", () => {
  assert.equal(normalizeResource("departments"), "company");
  assert.equal(normalizeResource("accounts"), "auth");
  assert.equal(normalizeResource("notifications"), "notifications");
  assert.equal(normalizeResource(""), "global");
});

test("resourcesMatch refreshes only matching resources", () => {
  assert.equal(resourcesMatch("payroll", "payroll"), true);
  assert.equal(resourcesMatch("payroll", ["payroll", "company"]), true);
  assert.equal(resourcesMatch("company", ["teams", "company"]), true);
  assert.equal(resourcesMatch("attendance", ["leave", "teams"]), false);
  assert.equal(resourcesMatch("anything", "global"), true);
});
