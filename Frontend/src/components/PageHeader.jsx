export default function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="page-header">
      <div className="min-w-0">
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h2 className="mt-1 font-extrabold text-ink-900">{title}</h2>
        {description && <p className="mt-2 text-sm leading-6 text-ink-500">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
