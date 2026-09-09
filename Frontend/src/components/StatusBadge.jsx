const STATUS_STYLES = {
  OPEN: "bg-brand-red-light text-brand-red",
  IN_PROGRESS: "bg-brand-amber-light text-brand-amber",
  RESOLVED: "bg-brand-green-light text-brand-green",
  PENDING: "bg-brand-amber-light text-brand-amber",
  COMPLETED: "bg-brand-green-light text-brand-green",
  APPROVED: "bg-brand-green-light text-brand-green",
  REJECTED: "bg-brand-red-light text-brand-red",
  CANCELLED: "bg-slate-100 text-ink-500",
  ACTIVE: "bg-brand-green-light text-brand-green",
  DRAFT: "bg-slate-100 text-ink-500",
  HOD_APPROVED: "bg-brand-green-light text-brand-green",
  PENDING_APPROVAL: "bg-brand-amber-light text-brand-amber",
  INCOMPLETE: "bg-brand-amber-light text-brand-amber",
  ABSENT: "bg-brand-red-light text-brand-red",
  PRESENT: "bg-brand-green-light text-brand-green",
};

const STATUS_LABELS = {
  IN_PROGRESS: "In Progress",
  HOD_APPROVED: "Approved",
  PENDING_APPROVAL: "Pending Approval",
};

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || "bg-slate-100 text-ink-500";
  const label = STATUS_LABELS[status] || (status ? status.charAt(0) + status.slice(1).toLowerCase() : "");
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}
