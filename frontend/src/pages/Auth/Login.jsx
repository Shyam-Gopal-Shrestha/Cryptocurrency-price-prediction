// import { useState, useContext } from "react";
// import axios from "axios";
// import { AuthContext } from "../../context/AuthContext";
// import { useNavigate } from "react-router-dom";

// export default function Login() {
//   const [form, setForm] = useState({ email: "", password: "" });
//   const { login } = useContext(AuthContext);
//   const navigate = useNavigate();

//   const handleSubmit = async (e) => {
//     e.preventDefault();

//     const res = await axios.post("http://127.0.0.1:8000/login", form);

//     login(res.data);

//     if (res.data.role === "admin") navigate("/admin");
//     else if (res.data.role === "researcher") navigate("/researcher");
//     else navigate("/user");
//   };

//   return (
//     <form onSubmit={handleSubmit}>
//       <input
//         placeholder="Email"
//         onChange={(e) => setForm({ ...form, email: e.target.value })}
//       />
//       <input
//         type="password"
//         placeholder="Password"
//         onChange={(e) => setForm({ ...form, password: e.target.value })}
//       />
//       <button>Login</button>
//     </form>
//   );
// }

import { useState } from "react";
import "./Login.css";

export default function Login() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [touched, setTouched] = useState({ email: false, password: false });

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError("");
  };

  const handleBlur = (e) => {
    setTouched((prev) => ({ ...prev, [e.target.name]: true }));
  };

  const validate = () => {
    if (!form.email.includes("@")) return "Please enter a valid email address.";
    if (form.password.length < 6)
      return "Password must be at least 6 characters.";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched({ email: true, password: true });
    const err = validate();
    if (err) {
      setError(err);
      return;
    }

    setLoading(true);
    setError("");
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1800));
    setLoading(false);
    // Replace with real auth logic
    alert("Login successful!");
  };

  const emailInvalid = touched.email && !form.email.includes("@");
  const passwordInvalid =
    touched.password && form.password.length > 0 && form.password.length < 6;

  return (
    <div className="login-root">
      {/* Geometric background decoration */}
      <div className="login-bg">
        <div className="login-bg__ring login-bg__ring--1" />
        <div className="login-bg__ring login-bg__ring--2" />
        <div className="login-bg__ring login-bg__ring--3" />
        <div className="login-bg__line login-bg__line--h" />
        <div className="login-bg__line login-bg__line--v" />
      </div>

      <div className="login-card">
        {/* Brand */}
        <div className="login-brand">
          <div className="login-brand__mark">
            <span className="login-brand__inner" />
          </div>
          <span className="login-brand__name">Nexus</span>
        </div>

        <div className="login-header">
          <h1 className="login-title">Welcome back</h1>
          <p className="login-subtitle">
            Sign in to continue to your workspace
          </p>
        </div>

        {error && (
          <div className="login-error" role="alert">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6.5" stroke="currentColor" />
              <path
                d="M7 4v3.5M7 9.5v.5"
                stroke="currentColor"
                strokeLinecap="round"
              />
            </svg>
            {error}
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          {/* Email */}
          <div
            className={`login-field ${emailInvalid ? "login-field--error" : ""} ${form.email && !emailInvalid ? "login-field--valid" : ""}`}
          >
            <label className="login-label" htmlFor="email">
              Email
            </label>
            <div className="login-input-wrap">
              <svg
                className="login-input-icon"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
              >
                <path
                  d="M2 4.5A1.5 1.5 0 013.5 3h9A1.5 1.5 0 0114 4.5v7A1.5 1.5 0 0112.5 13h-9A1.5 1.5 0 012 11.5v-7z"
                  stroke="currentColor"
                />
                <path
                  d="M2 5l6 4 6-4"
                  stroke="currentColor"
                  strokeLinecap="round"
                />
              </svg>
              <input
                id="email"
                type="email"
                name="email"
                className="login-input"
                placeholder="you@company.com"
                value={form.email}
                onChange={handleChange}
                onBlur={handleBlur}
                autoComplete="email"
                required
              />
              {form.email && !emailInvalid && (
                <svg
                  className="login-input-check"
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                >
                  <path
                    d="M2.5 7l3 3 6-6"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </div>
            {emailInvalid && (
              <span className="login-field-msg">
                Enter a valid email address
              </span>
            )}
          </div>

          {/* Password */}
          <div
            className={`login-field ${passwordInvalid ? "login-field--error" : ""} ${form.password.length >= 6 && touched.password ? "login-field--valid" : ""}`}
          >
            <label className="login-label" htmlFor="password">
              Password
              <a
                href="#"
                className="login-forgot"
                tabIndex={0}
                onClick={(e) => e.preventDefault()}
              >
                Forgot password?
              </a>
            </label>
            <div className="login-input-wrap">
              <svg
                className="login-input-icon"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
              >
                <rect
                  x="3"
                  y="7"
                  width="10"
                  height="7"
                  rx="1.5"
                  stroke="currentColor"
                />
                <path
                  d="M5 7V5a3 3 0 016 0v2"
                  stroke="currentColor"
                  strokeLinecap="round"
                />
                <circle cx="8" cy="10.5" r="1" fill="currentColor" />
              </svg>
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                name="password"
                className="login-input"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
                onBlur={handleBlur}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="login-toggle-pw"
                onClick={() => setShowPassword((p) => !p)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path
                      d="M2 2l12 12M6.5 6.6A2 2 0 0110 10M4.2 4.3C2.9 5.3 2 6.6 2 8c0 2.2 2.7 5 6 5 1.3 0 2.5-.4 3.5-1M6 3.2C6.6 3.1 7.3 3 8 3c3.3 0 6 2.8 6 5a6.4 6.4 0 01-1.4 3"
                      stroke="currentColor"
                      strokeLinecap="round"
                    />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path
                      d="M2 8c0-2.2 2.7-5 6-5s6 2.8 6 5-2.7 5-6 5-6-2.8-6-5z"
                      stroke="currentColor"
                    />
                    <circle cx="8" cy="8" r="2" stroke="currentColor" />
                  </svg>
                )}
              </button>
            </div>
            {passwordInvalid && (
              <span className="login-field-msg">
                Must be at least 6 characters
              </span>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            className={`login-btn ${loading ? "login-btn--loading" : ""}`}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="login-spinner" />
                Signing in…
              </>
            ) : (
              <>
                Sign in
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path
                    d="M3 7h8M7.5 3.5L11 7l-3.5 3.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </>
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="login-divider">
          <span>or continue with</span>
        </div>

        {/* Social */}
        <div className="login-social">
          <button
            type="button"
            className="login-social-btn"
            aria-label="Sign in with Google"
          >
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path
                d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
                fill="#4285F4"
              />
              <path
                d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z"
                fill="#34A853"
              />
              <path
                d="M3.964 10.706A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.038l3.007-2.332z"
                fill="#FBBC05"
              />
              <path
                d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58z"
                fill="#EA4335"
              />
            </svg>
            Google
          </button>
          <button
            type="button"
            className="login-social-btn"
            aria-label="Sign in with GitHub"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
            </svg>
            GitHub
          </button>
        </div>

        <p className="login-signup">
          Don't have an account?{" "}
          <a href="#" onClick={(e) => e.preventDefault()}>
            Create one free
          </a>
        </p>
      </div>
    </div>
  );
}
