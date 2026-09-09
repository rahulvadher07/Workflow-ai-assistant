export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex min-h-[240px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-[#cfe1db] bg-[#fbfefd] px-6 py-12 text-center">
      {Icon && <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"><Icon className="h-6 w-6" strokeWidth={1.6} /></div>}
      <p className="mt-1 text-sm font-bold text-ink-700">{title}</p>
      {description && <p className="max-w-md text-sm leading-6 text-ink-500">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
