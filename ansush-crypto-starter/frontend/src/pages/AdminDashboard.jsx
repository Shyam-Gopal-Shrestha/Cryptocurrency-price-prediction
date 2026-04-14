import React from "react";
import Navbar from "../components/Navbar";

export default function AdminDashboard() {
  const user = JSON.parse(localStorage.getItem("authUser"));

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <h1>Admin Dashboard</h1>
        <p>Welcome, {user?.username || "Admin"}.</p>

        <div style={styles.grid}>
          <div style={styles.card}>
            <h3>User Management</h3>
            <p>Monitor user roles, registrations, and access control.</p>
          </div>

          <div style={styles.card}>
            <h3>System Overview</h3>
            <p>Track application status and platform-level activity.</p>
          </div>

          <div style={styles.card}>
            <h3>Administrative Controls</h3>
            <p>Manage platform-level operations and future settings.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#0b1220", color: "white" },
  container: { maxWidth: "1100px", margin: "0 auto", padding: "40px 20px" },
  grid: {
    marginTop: "24px",
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
    gap: "20px",
  },
  card: {
    background: "#111827",
    border: "1px solid #334155",
    borderRadius: "16px",
    padding: "24px",
  },
};