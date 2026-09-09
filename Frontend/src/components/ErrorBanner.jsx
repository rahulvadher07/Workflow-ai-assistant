import { AlertTriangle } from "lucide-react";

export default function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-brand-red-light px-3.5 py-2.5 text-sm text-brand-red" role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p>{message}</p>
        <p className="mt-1 text-xs opacity-75">No data was changed by this failed request. Please try again.</p>
      </div>
    </div>
  );
}
