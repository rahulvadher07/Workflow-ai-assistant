import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Button from "../../components/Button";
import ErrorBanner from "../../components/ErrorBanner";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const result = await login(username, password);
    setLoading(false);
    if (result.success) {
      navigate("/");
    } else {
      setError(result.message);
    }
  }

  return (
    <div className="auth-form-shell">
      <div className="mb-7">
        <div className="mb-3 inline-flex items-center rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-[10px] font-extrabold uppercase tracking-[.12em] text-emerald-700">Secure workspace</div>
        <h2 className="text-2xl font-extrabold tracking-[-.035em] text-ink-900">Welcome back</h2>
      <p className="mt-2 text-sm leading-6 text-ink-500">Sign in to continue to your people operations workspace.</p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {error && <ErrorBanner message={error} />}

        <div>
          <label htmlFor="username" className="mb-1.5 block text-sm font-medium text-ink-700">
            Username
          </label>
          <input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="focus-ring w-full rounded-xl border border-border-subtle px-3.5 py-3 text-sm"
            autoComplete="username"
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink-700">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="focus-ring w-full rounded-xl border border-border-subtle px-3.5 py-3 text-sm"
            autoComplete="current-password"
          />
        </div>

        <Button type="submit" loading={loading} className="w-full">
          Sign in
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-ink-500">
        New employee?{" "}
        <Link to="/register" className="font-medium text-sky-600 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
