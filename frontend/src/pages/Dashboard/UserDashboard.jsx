// src/pages/UserDashboard.jsx
import React, { useState, useEffect } from "react";
import api from "../../api/axios";
import PredictionForm from "../../components/PredictionForm";

export default function UserDashboard() {
  const [historical, setHistorical] = useState([]);
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [historicalError, setHistoricalError] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("BTC-USD");

  useEffect(() => {
    const fetchHistorical = async () => {
      setLoadingHistorical(true);
      setHistoricalError("");
      try {
        const res = await api.get("/historical", {
          params: { symbol: selectedSymbol },
        });
        setHistorical(res.data);
      } catch (err) {
        console.error(err);
        setHistoricalError("Failed to load historical data");
      } finally {
        setLoadingHistorical(false);
      }
    };

    fetchHistorical();
  }, [selectedSymbol]);

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h2>📊 Crypto Prediction Dashboard</h2>

      {/* Prediction Form */}
      <PredictionForm />

      {/* Historical Data */}
      <div style={{ marginTop: "30px" }}>
        <h3>📉 Historical Data</h3>
        <label style={{ marginRight: "8px" }}>Crypto:</label>
        <select
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
          style={{ marginBottom: "12px" }}
        >
          <option value="BTC-USD">Bitcoin</option>
          <option value="ETH-USD">Ethereum</option>
          <option value="SOL-USD">Solana</option>
          <option value="ADA-USD">Cardano</option>
        </select>
        {loadingHistorical ? (
          <p>Loading historical data...</p>
        ) : historicalError ? (
          <p style={{ color: "red" }}>{historicalError}</p>
        ) : historical.length > 0 ? (
          <table border="1" cellPadding="5">
            <thead>
              <tr>
                <th>Date</th>
                <th>Open</th>
                <th>High</th>
                <th>Low</th>
                <th>Close</th>
                <th>Volume</th>
              </tr>
            </thead>
            <tbody>
              {historical.map((item, index) => (
                <tr key={index}>
                  <td>{item.Date}</td>
                  <td>{item.Open}</td>
                  <td>{item.High}</td>
                  <td>{item.Low}</td>
                  <td>{item.Close}</td>
                  <td>{item.Volume}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No historical data available</p>
        )}
      </div>
    </div>
  );
}
