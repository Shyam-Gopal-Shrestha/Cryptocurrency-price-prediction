import { Link } from 'react-router-dom'

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="page-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-icon">₿</div>
            <h1>Ansush <span>Cryptocurrency Price Prediction</span></h1>
          </div>
          <nav className="nav-links">
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </nav>
        </div>
      </header>
      <main className="page-wrapper">
        <section className="auth-card">
          <div className="auth-header">
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
          {children}
          {footer ? <div className="auth-footer">{footer}</div> : null}
        </section>
      </main>
    </div>
  )
}
