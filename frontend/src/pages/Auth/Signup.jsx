import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import "./signup.css";

export default function Signup() {
  const [form, setForm] = useState({ email: "", password: "", role: "user" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState({ email: false, password: false });

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError("");
    setSuccess("");
  };

  const handleBlur = (e) => {
    setTouched((prev) => ({ ...prev, [e.target.name]: true }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched({ email: true, password: true });
    setError("");
    setSuccess("");

    if (!form.email.trim() || !form.password.trim()) {
      setError("Email and password are required.");
      return;
    }
    if (!form.email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    if (form.password.trim().length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    try {
      await axios.post("http://127.0.0.1:8000/signup", form);
      setSuccess("Account created! You can now log in.");
      setForm({ email: "", password: "", role: "user" });
      setTouched({ email: false, password: false });
    } catch (err) {
      setError(
        err.response?.data?.detail || "Signup failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const emailInvalid =
    touched.email && !form.email.includes("@") && form.email.length > 0;
  const passwordInvalid =
    touched.password && form.password.length > 0 && form.password.length < 6;

  return (
    <div className="signup-root">
      {/* Background — same rings as Login & Home */}
      <div className="signup-bg">
        <div className="signup-bg__ring signup-bg__ring--1" />
        <div className="signup-bg__ring signup-bg__ring--2" />
        <div className="signup-bg__ring signup-bg__ring--3" />
        <div className="signup-bg__line signup-bg__line--h" />
        <div className="signup-bg__line signup-bg__line--v" />
      </div>

      <div className="signup-card">
        {/* Brand */}
        <div className="signup-brand">
          <div className="signup-brand__mark">
            <span className="signup-brand__inner" />
          </div>
          <span className="signup-brand__name">
            Ansush <span className="signup-brand__accent">Crypto</span>
          </span>
        </div>

        <div className="signup-header">
          <h1 className="signup-title">Create account</h1>
          <p className="signup-subtitle">
            Start predicting crypto prices in minutes
          </p>
        </div>

        {/* Error / Success banners */}
        {error && (
          <div className="signup-banner signup-banner--error" role="alert">
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
        {success && (
          <div className="signup-banner signup-banner--success" role="status">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6.5" stroke="currentColor" />
              <path
                d="M4 7l2.5 2.5L10 5"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {success}
          </div>
        )}

        <form className="signup-form" onSubmit={handleSubmit} noValidate>
          {/* Email */}
          <div
            className={`signup-field ${emailInvalid ? "signup-field--error" : ""} ${form.email && !emailInvalid && touched.email ? "signup-field--valid" : ""}`}
          >
            <label className="signup-label" htmlFor="su-email">
              Email
            </label>
            <div className="signup-input-wrap">
              <svg
                className="signup-input-icon"
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
                id="su-email"
                type="email"
                name="email"
                className="signup-input"
                placeholder="you@company.com"
                value={form.email}
                onChange={handleChange}
                onBlur={handleBlur}
                autoComplete="email"
                required
              />
              {form.email && !emailInvalid && touched.email && (
                <svg
                  className="signup-input-check"
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
              <span className="signup-field-msg">
                Enter a valid email address
              </span>
            )}
          </div>

          {/* Password */}
          <div
            className={`signup-field ${passwordInvalid ? "signup-field--error" : ""} ${form.password.length >= 6 && touched.password ? "signup-field--valid" : ""}`}
          >
            <label className="signup-label" htmlFor="su-password">
              Password
            </label>
            <div className="signup-input-wrap">
              <svg
                className="signup-input-icon"
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
                id="su-password"
                type={showPassword ? "text" : "password"}
                name="password"
                className="signup-input"
                placeholder="Min 6 characters"
                value={form.password}
                onChange={handleChange}
                onBlur={handleBlur}
                autoComplete="new-password"
                minLength={6}
                required
              />
              <button
                type="button"
                className="signup-toggle-pw"
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
              <span className="signup-field-msg">
                Must be at least 6 characters
              </span>
            )}
          </div>

          {/* Role */}
          <div className="signup-field">
            <label className="signup-label" htmlFor="su-role">
              Account type
            </label>
            <div className="signup-input-wrap">
              <svg
                className="signup-input-icon"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
              >
                <circle cx="8" cy="5" r="2.5" stroke="currentColor" />
                <path
                  d="M2.5 13c0-2.485 2.462-4.5 5.5-4.5s5.5 2.015 5.5 4.5"
                  stroke="currentColor"
                  strokeLinecap="round"
                />
              </svg>
              <select
                id="su-role"
                name="role"
                className="signup-input signup-select"
                value={form.role}
                onChange={handleChange}
              >
                <option value="user">User</option>
                <option value="researcher">Researcher</option>
              </select>
              <svg
                className="signup-select-arrow"
                width="12"
                height="12"
                viewBox="0 0 12 12"
                fill="none"
              >
                <path
                  d="M3 4.5L6 7.5L9 4.5"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className={`signup-btn ${loading ? "signup-btn--loading" : ""}`}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="signup-spinner" />
                Creating account…
              </>
            ) : (
              <>
                Create account
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

        <p className="signup-login">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
