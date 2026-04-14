import React from "react";
import Navbar from "../components/Navbar";

export default function ResearcherDashboard() {
  const user = JSON.parse(localStorage.getItem("authUser"));

  return (
    <div style={styles.page}>
      <Navbar />
      <div style={styles.container}>
        <h1>Researcher Dashboard</h1>
        <p>Welcome, {user?.username || "Researcher"}.</p>

        <div style={styles.grid}>
          <div style={styles.card}>
            <h3>Model Insights</h3>
            <p>Review prediction behavior, feature impact, and output trends.</p>
          </div>

          <div style={styles.card}>
            <h3>Experimental Results</h3>
            <p>Compare forecasting approaches and evaluation summaries.</p>
          </div>

          <div style={styles.card}>
            <h3>Data Exploration</h3>
            <p>Inspect datasets, indicators, and analytical outputs.</p>
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