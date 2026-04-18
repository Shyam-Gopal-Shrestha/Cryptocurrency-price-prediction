import { Link } from "react-router-dom";
import "./Home.css";

export default function Home() {
  return (
    <div className="home-root">
      {/* Background rings — same as Login */}
      <div className="home-bg">
        <div className="home-bg__ring home-bg__ring--1" />
        <div className="home-bg__ring home-bg__ring--2" />
        <div className="home-bg__ring home-bg__ring--3" />
        <div className="home-bg__line home-bg__line--h" />
        <div className="home-bg__line home-bg__line--v" />
      </div>

      {/* Header */}
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark">
              <span className="brand-mark__inner" />
            </div>
            <span className="brand-name">
              Ansush <span className="brand-accent">Crypto</span>
            </span>
          </div>

          <nav className="nav-links">
            <Link to="/" className="nav-link nav-link--active">
              Home
            </Link>
            <Link to="/login" className="nav-link">
              Login
            </Link>
            <Link to="/signup" className="nav-link nav-link--cta">
              Register
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="hero">
        <div className="hero-badge">
          <span className="hero-badge__dot" />
          Machine Learning Powered
        </div>

        <h1 className="hero-title">
          Predict the Future
          <br />
          <span className="hero-title--accent">of Crypto</span>
        </h1>

        <p className="hero-subtitle">
          Advanced price prediction using LSTM, XGBoost, and Random Forest
          models — built for traders and researchers.
        </p>

        <div className="hero-buttons">
          <Link to="/login" className="btn-primary">
            Get Started
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M3 7h8M7.5 3.5L11 7l-3.5 3.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>
          <Link to="/signup" className="btn-secondary">
            Create Account
          </Link>
        </div>

        {/* Stats row */}
        <div className="hero-stats">
          <div className="hero-stat">
            <span className="hero-stat__value">3</span>
            <span className="hero-stat__label">ML Models</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat">
            <span className="hero-stat__value">Real-time</span>
            <span className="hero-stat__label">Price Data</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat">
            <span className="hero-stat__value">Free</span>
            <span className="hero-stat__label">To Start</span>
          </div>
        </div>
      </main>
    </div>
  );
}
