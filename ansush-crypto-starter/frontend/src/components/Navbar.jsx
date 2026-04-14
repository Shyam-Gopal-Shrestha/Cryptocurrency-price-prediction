import React from "react";
import { Link, useNavigate } from "react-router-dom";
import logo from "../assets/ansush-logo.png";

export default function Navbar() {
  const navigate = useNavigate();
  const authUser = JSON.parse(localStorage.getItem("authUser"));

  const handleLogout = () => {
    localStorage.removeItem("authUser");
    navigate("/login");
  };

  return (
    <header style={styles.header}>
      <div style={styles.inner}>
        <Link to="/" style={styles.brandWrap}>
          <img src={logo} alt="Ansush Logo" style={styles.logo} />
        </Link>

        <nav style={styles.nav}>
          <Link to="/" style={styles.link}>Home</Link>

          {!authUser && <Link to="/login" style={styles.link}>Login</Link>}
          {!authUser && <Link to="/register" style={styles.link}>Register</Link>}

          {authUser?.role === "user" && (
            <Link to="/user-dashboard" style={styles.link}>User Dashboard</Link>
          )}

          {authUser?.role === "admin" && (
            <Link to="/admin-dashboard" style={styles.link}>Admin Dashboard</Link>
          )}

          {authUser?.role === "researcher" && (
            <Link to="/researcher-dashboard" style={styles.link}>Researcher Dashboard</Link>
          )}

          {authUser && (
            <button onClick={handleLogout} style={styles.logoutBtn}>
              Logout
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}

const styles = {
  header: {
    width: "100%",
    maxWidth: "100%",
    borderBottom: "1px solid rgba(100, 116, 139, 0.25)",
    background: "rgba(8, 20, 48, 0.96)",
    overflowX: "hidden",
    position: "sticky",
    top: 0,
    zIndex: 50,
    backdropFilter: "blur(10px)",
  },
  inner: {
    width: "100%",
    maxWidth: "1400px",
    margin: "0 auto",
    padding: "14px 20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    flexWrap: "wrap",
  },
  brandWrap: {
    display: "flex",
    alignItems: "center",
    textDecoration: "none",
  },
  logo: {
    width: "150px",
    height: "60px",
    objectFit: "contain",
    display: "block",
  },
  nav: {
    display: "flex",
    alignItems: "center",
    gap: "18px",
    flexWrap: "wrap",
  },
  link: {
    textDecoration: "none",
    color: "#ffffff",
    fontWeight: 500,
  },
  logoutBtn: {
    border: "none",
    background: "#dc2626",
    color: "#fff",
    padding: "10px 14px",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: 600,
  },
};