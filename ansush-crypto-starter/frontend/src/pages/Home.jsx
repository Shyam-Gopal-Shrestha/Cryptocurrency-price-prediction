import React from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import logo from "../assets/ansush-logo.png";

export default function Home() {
  return (
    <div style={styles.page}>
      <Navbar />

      <main style={styles.main}>
        <section style={styles.hero}>
          <div style={styles.card}>
            <div style={styles.heroLogoWrap}>
              <img src={logo} alt="Ansush Logo" style={styles.heroLogo} />
            </div>

            <h1 style={styles.title}>
              Welcome to Ansush Cryptocurrency Price Prediction
            </h1>

            <p style={styles.subtitle}>
              A professional platform for cryptocurrency forecasting, analytics,
              and role-based access for users, administrators, and researchers.
            </p>

            <div style={styles.buttonRow}>
              <Link to="/login" style={styles.primaryBtn}>
                Login
              </Link>
              <Link to="/register" style={styles.secondaryBtn}>
                Create Account
              </Link>
            </div>
          </div>
        </section>

        <section style={styles.statsSection}>
          <div style={styles.statsGrid}>
            <div style={styles.statCard}>
              <h3 style={styles.statNumber}>100,000+</h3>
              <p style={styles.statLabel}>Prediction Records</p>
            </div>

            <div style={styles.statCard}>
              <h3 style={styles.statNumber}>90%+</h3>
              <p style={styles.statLabel}>Analytical Confidence Tracking</p>
            </div>

            <div style={styles.statCard}>
              <h3 style={styles.statNumber}>3</h3>
              <p style={styles.statLabel}>Role-Based Dashboards</p>
            </div>
          </div>
        </section>

        <section style={styles.aboutSection}>
          <div style={styles.aboutCard}>
            <div style={styles.aboutTop}>
              <img src={logo} alt="Ansush Logo" style={styles.aboutLogo} />
              <div>
                <h2 style={styles.aboutTitle}>About Us</h2>
                <p style={styles.aboutTagline}>
                  Focused forecasting for a data-driven crypto experience.
                </p>
              </div>
            </div>

            <p style={styles.aboutText}>
              Ansush Cryptocurrency Price Prediction is designed to support
              cryptocurrency analysis through predictive modelling, structured
              insights, and role-based access. The platform is built for general
              users, administrators, and researchers who need a clean interface
              for exploring market trends, forecasts, and analytical outputs.
            </p>

            <p style={styles.aboutText}>
              Our goal is to combine forecasting, usability, and organized
              access control into one reliable environment that supports both
              learning and practical decision-making.
            </p>
          </div>
        </section>
      </main>

      <footer style={styles.footer}>
        <div style={styles.footerInner}>
          <div style={styles.footerBrand}>
            <div style={styles.footerBrandTop}>
              <img src={logo} alt="Ansush Logo" style={styles.footerLogo} />
              <div>
                <h3 style={styles.footerTitle}>Ansush</h3>
                <p style={styles.footerSub}>Cryptocurrency Price Prediction</p>
              </div>
            </div>
            <p style={styles.footerText}>
              A forecasting platform for crypto insights, predictive modelling,
              and role-based analysis.
            </p>
          </div>

          <div>
            <h4 style={styles.footerHeading}>Quick Links</h4>
            <ul style={styles.footerList}>
              <li><Link to="/" style={styles.footerLink}>Home</Link></li>
              <li><Link to="/login" style={styles.footerLink}>Login</Link></li>
              <li><Link to="/register" style={styles.footerLink}>Register</Link></li>
            </ul>
          </div>

          <div>
            <h4 style={styles.footerHeading}>Resources</h4>
            <ul style={styles.footerList}>
              <li style={styles.footerText}>Forecasting Dashboard</li>
              <li style={styles.footerText}>Research Insights</li>
              <li style={styles.footerText}>System Access</li>
            </ul>
          </div>

          <div>
            <h4 style={styles.footerHeading}>Contact</h4>
            <ul style={styles.footerList}>
              <li style={styles.footerText}>Email: support@ansushcrypto.com</li>
              <li style={styles.footerText}>Location: Project Workspace</li>
              <li style={styles.footerText}>Availability: 24/7 Platform Access</li>
            </ul>
          </div>
        </div>

        <div style={styles.footerBottom}>
          © 2026 Ansush Cryptocurrency Price Prediction. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    width: "100%",
    maxWidth: "100%",
    overflowX: "hidden",
    background: "linear-gradient(135deg, #071127, #0a1630, #101d3a)",
    color: "#ffffff",
  },
  main: {
    width: "100%",
    maxWidth: "100%",
  },
  hero: {
    width: "100%",
    padding: "60px 20px 30px",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
  },
  card: {
    width: "100%",
    maxWidth: "1100px",
    padding: "56px 32px",
    borderRadius: "28px",
    background: "rgba(8, 20, 48, 0.88)",
    border: "1px solid rgba(100, 116, 139, 0.35)",
    boxShadow: "0 25px 60px rgba(0, 0, 0, 0.28)",
    textAlign: "center",
  },
  
  heroLogoWrap: {
  display: "flex",
  justifyContent: "center",
  marginBottom: "18px",
    },

    heroLogo: {
    width: "180px",
    height: "180px",
    objectFit: "contain",
    filter: "drop-shadow(0 0 18px rgba(34, 211, 238, 0.25))",
    },

    aboutLogo: {
    width: "80px",
    height: "80px",
    objectFit: "contain",
    },

  title: {
    margin: 0,
    fontSize: "clamp(2rem, 4vw, 4rem)",
    lineHeight: 1.2,
    fontWeight: 700,
  },
  subtitle: {
    margin: "24px auto 0",
    maxWidth: "850px",
    fontSize: "clamp(1rem, 1.6vw, 1.2rem)",
    lineHeight: 1.8,
    color: "#dbe4f0",
  },
  buttonRow: {
    marginTop: "32px",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "16px",
    flexWrap: "wrap",
  },
  primaryBtn: {
    textDecoration: "none",
    padding: "14px 26px",
    borderRadius: "14px",
    background: "linear-gradient(135deg, #2563eb, #06b6d4)",
    color: "#ffffff",
    fontWeight: 700,
    minWidth: "150px",
  },
  secondaryBtn: {
    textDecoration: "none",
    padding: "14px 26px",
    borderRadius: "14px",
    background: "rgba(30, 41, 59, 0.95)",
    border: "1px solid rgba(148, 163, 184, 0.35)",
    color: "#ffffff",
    fontWeight: 700,
    minWidth: "150px",
  },
  statsSection: {
    padding: "10px 20px 30px",
  },
  statsGrid: {
    width: "100%",
    maxWidth: "1100px",
    margin: "0 auto",
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "20px",
  },
  statCard: {
    background: "rgba(8, 20, 48, 0.88)",
    border: "1px solid rgba(100, 116, 139, 0.35)",
    borderRadius: "20px",
    padding: "26px",
    textAlign: "center",
  },
  statNumber: {
    margin: 0,
    fontSize: "2rem",
    color: "#67e8f9",
  },
  statLabel: {
    marginTop: "10px",
    color: "#dbe4f0",
  },
  aboutSection: {
    padding: "10px 20px 70px",
  },
  aboutCard: {
    width: "100%",
    maxWidth: "1100px",
    margin: "0 auto",
    background: "rgba(8, 20, 48, 0.88)",
    border: "1px solid rgba(100, 116, 139, 0.35)",
    borderRadius: "24px",
    padding: "32px",
  },
  aboutTop: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    flexWrap: "wrap",
    marginBottom: "20px",
  },
  aboutLogo: {
    width: "70px",
    height: "70px",
    objectFit: "contain",
  },
  aboutTitle: {
    margin: 0,
    fontSize: "1.9rem",
  },
  aboutTagline: {
    margin: "6px 0 0",
    color: "#7dd3fc",
  },
  aboutText: {
    lineHeight: 1.9,
    color: "#dbe4f0",
    marginBottom: "14px",
  },
  footer: {
    borderTop: "1px solid rgba(100, 116, 139, 0.25)",
    background: "rgba(5, 12, 28, 0.95)",
    paddingTop: "32px",
  },
  footerInner: {
    width: "100%",
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "0 20px 24px",
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "28px",
  },
  footerBrand: {},
  footerBrandTop: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "12px",
  },
  footerLogo: {
    width: "50px",
    height: "50px",
    objectFit: "contain",
  },
  footerTitle: {
    margin: 0,
    fontSize: "1.2rem",
  },
  footerSub: {
    margin: 0,
    color: "#7dd3fc",
    fontSize: "0.85rem",
  },
  footerHeading: {
    marginTop: 0,
    marginBottom: "12px",
    fontSize: "1rem",
  },
  footerList: {
    listStyle: "none",
    padding: 0,
    margin: 0,
    display: "grid",
    gap: "10px",
  },
  footerLink: {
    textDecoration: "none",
    color: "#dbe4f0",
  },
  footerText: {
    color: "#cbd5e1",
    margin: 0,
    lineHeight: 1.7,
  },
  footerBottom: {
    textAlign: "center",
    color: "#94a3b8",
    borderTop: "1px solid rgba(100, 116, 139, 0.2)",
    padding: "16px 20px 22px",
    fontSize: "0.92rem",
  },
};