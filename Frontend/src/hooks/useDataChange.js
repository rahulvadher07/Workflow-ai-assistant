import { useEffect, useRef } from "react";
import { DATA_CHANGED_EVENT, DATA_CHANGED_CHANNEL, resourcesMatch } from "../services/dataChangeBus";

/**
 * Event-driven UI invalidation. Mounted consumers reload only their resource.
 * No polling, timers, focus synchronization or page reloads are used.
 */
export function useDataChange(onChange, resources = "global") {
  const callbackRef = useRef(onChange);
  callbackRef.current = onChange;
  const resourceList = Array.isArray(resources) ? resources : [resources];

  useEffect(() => {
    const queued = new Set();
    const run = (resource) => {
      if (!resourcesMatch(resource, resourceList) || queued.has(resource)) return;
      queued.add(resource);
      queueMicrotask(() => {
        queued.delete(resource);
        Promise.resolve(callbackRef.current?.()).catch(() => {});
      });
    };

    const handler = (event) => run(event?.detail?.resource || "global");
    window.addEventListener(DATA_CHANGED_EVENT, handler);

    let channel = null;
    if (typeof window !== "undefined" && "BroadcastChannel" in window) {
      try {
        channel = new BroadcastChannel(DATA_CHANGED_CHANNEL);
        channel.onmessage = (event) => run(event?.data?.resource || "global");
      } catch {
        channel = null;
      }
    }

    return () => {
      window.removeEventListener(DATA_CHANGED_EVENT, handler);
      channel?.close();
    };
  }, [resourceList.join("|")]);
}

export { DATA_CHANGED_EVENT, DATA_CHANGED_CHANNEL };
