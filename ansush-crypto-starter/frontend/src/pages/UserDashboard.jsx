import React from "react";
import Navbar from "../components/Navbar";

export default function UserDashboard() {
  const user = JSON.parse(localStorage.getItem("authUser"));

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <h1>User Dashboard</h1>
        <p>Welcome, {user?.username || "User"}.</p>

        <div style={styles.grid}>
          <div style={styles.card}>
            <h3>Market Overview</h3>
            <p>View cryptocurrency summaries and prediction highlights.</p>
          </div>

          <div style={styles.card}>
            <h3>Forecast Access</h3>
            <p>Access model-based next-step forecasts and chart outputs.</p>
          </div>

          <div style={styles.card}>
            <h3>Personal Activity</h3>
            <p>Track your saved preferences and future dashboard interactions.</p>
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