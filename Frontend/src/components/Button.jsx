const VARIANTS = {
  primary: "bg-sky-600 text-white shadow-[0_10px_22px_rgba(5,159,136,.20)] hover:bg-emerald-700 disabled:bg-emerald-300",
  secondary: "border border-border-subtle bg-white/90 text-ink-700 shadow-sm hover:border-[#b9d5ce] hover:bg-[#f7fbfa] disabled:text-ink-400",
  danger: "bg-brand-red text-white shadow-sm hover:bg-red-700 disabled:bg-red-300",
  ghost: "text-ink-700 hover:bg-emerald-50/80 disabled:text-ink-400",
};

export default function Button({ variant = "primary", className = "", children, loading, disabled, ...props }) {
  return (
    <button
      className={`focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all duration-150 disabled:cursor-not-allowed disabled:transform-none ${VARIANTS[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  );
}
