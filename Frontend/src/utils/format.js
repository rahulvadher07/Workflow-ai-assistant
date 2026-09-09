export function formatMinutesAsHours(minutes) {
  if (minutes == null) return "-";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

export function formatTime(isoString) {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(isoString) {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleDateString([], { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(isoString) {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function formatCurrency(value) {
  if (value == null) return "-";
  return `\u20b9${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function monthLabel(year, month) {
  return new Date(year, month - 1, 1).toLocaleDateString([], { month: "long", year: "numeric" });
}
