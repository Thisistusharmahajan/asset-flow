import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import "./Login.css";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [mode, setMode] = useState("login"); // 'login' | 'signup'
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const result =
        mode === "login"
          ? await api.login(form.email, form.password)
          : await api.signup(form.name, form.email, form.password);
      login(result.token, result.user);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-mark">
          <span className="login-mark-tag">AF-0001</span>
          <div className="login-mark-badge">AF</div>
        </div>

        <h1 className="login-title">AssetFlow</h1>
        <p className="login-subtitle">
          {mode === "login" ? "Sign in to your workspace" : "Create your employee account"}
        </p>

        <form onSubmit={handleSubmit} className="login-form">
          {mode === "signup" && (
            <label className="login-field">
              <span>Full name</span>
              <input
                type="text"
                value={form.name}
                onChange={update("name")}
                placeholder="Priya Shah"
                required
              />
            </label>
          )}

          <label className="login-field">
            <span>Email</span>
            <input
              type="email"
              value={form.email}
              onChange={update("email")}
              placeholder="name@company.com"
              autoComplete="email"
              required
            />
          </label>

          <label className="login-field">
            <span>Password</span>
            <input
              type="password"
              value={form.password}
              onChange={update("password")}
              placeholder="••••••••••"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={mode === "signup" ? 8 : undefined}
              required
            />
          </label>

          {mode === "login" && (
            <div className="login-forgot">
              <button type="button" className="link-button">
                Forgot password
              </button>
            </div>
          )}

          {error && <div className="login-error" role="alert">{error}</div>}

          <button type="submit" className="login-submit" disabled={submitting}>
            {submitting
              ? "Please wait…"
              : mode === "login"
              ? "Sign in"
              : "Create account"}
          </button>
        </form>

        <div className="login-divider" />

        {mode === "login" ? (
          <div className="login-switch">
            <p className="login-switch-title">New here?</p>
            <p className="login-switch-copy">
              Signup creates an employee account. Admin roles are assigned later
              from the Employee Directory.
            </p>
            <button
              type="button"
              className="login-secondary"
              onClick={() => {
                setMode("signup");
                setError("");
              }}
            >
              Create account
            </button>
          </div>
        ) : (
          <div className="login-switch">
            <p className="login-switch-copy">Already have an account?</p>
            <button
              type="button"
              className="login-secondary"
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Sign in instead
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
