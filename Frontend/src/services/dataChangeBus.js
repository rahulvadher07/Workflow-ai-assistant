export const DATA_CHANGED_EVENT = "workflow_ai_data_changed";
export const DATA_CHANGED_CHANNEL = "workflow_ai_data_changed_channel";

export const RESOURCE_ALIASES = Object.freeze({
  auth: "auth",
  accounts: "auth",
  company: "company",
  departments: "company",
  knowledge: "company",
  attendance: "attendance",
  leave: "leave",
  workspace: "workspace",
  teams: "teams",
  payroll: "payroll",
  notifications: "notifications",
  global: "global",
});

export function normalizeResource(resource = "global") {
  const value = String(resource || "global").trim().toLowerCase();
  return RESOURCE_ALIASES[value] || value || "global";
}

export function resourcesMatch(resource, resources) {
  const actual = normalizeResource(resource);
  const wanted = Array.isArray(resources) ? resources : [resources];
  return wanted.some((item) => {
    const normalized = normalizeResource(item);
    return normalized === "global" || normalized === actual || actual === "global";
  });
}

export function emitDataChange(detail = {}) {
  if (typeof window === "undefined") return;
  const payload = { ...detail, resource: normalizeResource(detail.resource) };
  window.dispatchEvent(new CustomEvent(DATA_CHANGED_EVENT, { detail: payload }));
  if ("BroadcastChannel" in window) {
    try {
      const channel = new BroadcastChannel(DATA_CHANGED_CHANNEL);
      channel.postMessage(payload);
      channel.close();
    } catch {
      // Optional cross-tab capability; same-tab event remains authoritative.
    }
  }
}
