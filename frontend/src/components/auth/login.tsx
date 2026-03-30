/* ------------------------------------------------------------------ */
/* Login form component                                                */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../../context/auth-context";

function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { login, isLoading, error } = useAuthContext();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    try {
      await login({ username, password });
      navigate("/", { replace: true });
    } catch {
      // Error is handled by the auth context
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-secondary p-4">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-500 text-white text-2xl font-bold">
            M
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
            Mosoro Dashboard
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Sign in to manage your robot fleet
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label htmlFor="username" className="label">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input"
              placeholder="Enter your username"
              required
              autoComplete="username"
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="password" className="label">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              placeholder="Enter your password"
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div
              className="rounded-md bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400"
              role="alert"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full"
          >
            {isLoading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-[var(--color-text-muted)]">
          Mosoro Communications Platform
        </p>
      </div>
    </div>
  );
}

export { Login };
