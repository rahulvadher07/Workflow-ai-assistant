import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { authService } from "../../services/authService";
import { companyService } from "../../services/companyService";
import { extractErrorMessage } from "../../services/apiClient";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";

export default function RegisterPage() {
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    username: "", email: "", first_name: "", last_name: "",
    password: "", department_id: "", employee_code: "", phone: "",
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    companyService.publicDepartments().then((res) => setDepartments(Array.isArray(res.data) ? res.data : [])).catch(() => {});
  }, []);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authService.register(form);
      setSubmitted(true);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex flex-col items-center py-4 text-center">
        <CheckCircle2 className="h-10 w-10 text-brand-green" />
        <h2 className="mt-3 text-base font-semibold text-ink-900">Account created successfully</h2>
        <p className="mt-1 text-sm text-ink-500">Waiting for HOD approval.</p>
        <Link to="/login" className="mt-5">
          <Button variant="secondary">Back to sign in</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="auth-form-shell">
      <div className="mb-7">
        <div className="mb-3 inline-flex items-center rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-[10px] font-extrabold uppercase tracking-[.12em] text-emerald-700">Join the workspace</div>
        <h2 className="text-2xl font-extrabold tracking-[-.035em] text-ink-900">Create your account</h2>
      <p className="mt-2 text-sm leading-6 text-ink-500">Set up your employee profile. Your registration will be reviewed before first sign in.</p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-3">
        {error && <ErrorBanner message={error} />}

        <div className="grid grid-cols-2 gap-3">
          <Field label="First name" value={form.first_name} onChange={(v) => update("first_name", v)} required />
          <Field label="Last name" value={form.last_name} onChange={(v) => update("last_name", v)} />
        </div>

        <Field label="Username" value={form.username} onChange={(v) => update("username", v)} required />
        <Field label="Email" type="email" value={form.email} onChange={(v) => update("email", v)} required />
        <Field label="Phone" value={form.phone} onChange={(v) => update("phone", v)} />
        <Field label="Employee code" value={form.employee_code} onChange={(v) => update("employee_code", v)} required />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-700">Department</label>
          <select
            required
            value={form.department_id}
            onChange={(e) => update("department_id", e.target.value)}
            className="focus-ring w-full rounded-xl border border-border-subtle px-3.5 py-3 text-sm"
          >
            <option value="">Select department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        <Field label="Password" type="password" value={form.password} onChange={(v) => update("password", v)} required />

        <Button type="submit" loading={loading} className="w-full !mt-5">
          Create account
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-ink-500">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-sky-600 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-ink-700">{label}</label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="focus-ring w-full rounded-xl border border-border-subtle px-3.5 py-3 text-sm"
      />
    </div>
  );
}
