import React, { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [form, setForm] = useState({
    symbol: "BTC-USD",
    Open: "",
    High: "",
    Low: "",
    Volume: "",
  });

  const [date, setDate] = useState("");
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [historicalError, setHistoricalError] = useState("");

  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({
      ...form,
      [name]: name === "symbol" ? value : value === "" ? "" : parseFloat(value),
    });
  };

  const handleDateChange = (e) => {
    setDate(e.target.value);
  };

  useEffect(() => {
    const loadHistorical = async () => {
      if (!date) return;

      setLoadingHistorical(true);
      setHistoricalError("");

      try {
        const res = await axios.get("http://127.0.0.1:8000/historical", {
          params: { symbol: form.symbol, date },
        });

        if (res.data.error) {
          setHistoricalError(res.data.error);
          return;
        }

        setForm((prev) => ({
          ...prev,
          Open: res.data.Open,
          High: res.data.High,
          Low: res.data.Low,
          Volume: res.data.Volume,
        }));
      } catch (err) {
        console.error(err);
        setHistoricalError("Failed to load historical data.");
      } finally {
        setLoadingHistorical(false);
      }
    };

    loadHistorical();
  }, [date, form.symbol]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setPrediction(null);
    setError("");

    try {
      const res = await axios.post("http://127.0.0.1:8000/predict", form);

      if (res.data.prediction) {
        setPrediction(res.data.prediction[0]);
      } else if (res.data.error) {
        setError(res.data.error);
      } else {
        setError("Unknown error from server");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch prediction. Check API.");
    }
  };

  return (
    <div
      style={{
        maxWidth: "400px",
        margin: "40px auto",
        padding: "20px",
        border: "1px solid #ddd",
        borderRadius: "8px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        fontFamily: "Arial, sans-serif",
        backgroundColor: "#f9f9f9",
      }}
    >
      <h2 style={{ textAlign: "center", marginBottom: "20px" }}>
        Crypto Price Prediction
      </h2>

      <form onSubmit={handleSubmit}>
        {/* Crypto Selector */}
        <label>
          Select Crypto:
          <select
            name="symbol"
            onChange={handleChange}
            value={form.symbol}
            style={{ width: "100%", padding: "8px", margin: "8px 0" }}
          >
            <option value="BTC-USD">Bitcoin</option>
            <option value="ETH-USD">Ethereum</option>
            <option value="SOL-USD">Solana</option>
            <option value="ADA-USD">Cardano</option>
          </select>
        </label>

        <label>
          Select Date:
          <input
            type="date"
            value={date}
            onChange={handleDateChange}
            style={{ width: "100%", padding: "8px", margin: "8px 0" }}
          />
        </label>

        {loadingHistorical && (
          <div style={{ color: "#555", margin: "8px 0" }}>
            Loading historical data...
          </div>
        )}

        {historicalError && (
          <div style={{ color: "#d8000c", margin: "8px 0" }}>
            {historicalError}
          </div>
        )}

        {/* Input fields */}
        <label>
          Open:
          <input
            name="Open"
            type="number"
            placeholder="Enter Open price"
            value={form.Open}
            onChange={handleChange}
            style={{ width: "100%", padding: "8px", margin: "8px 0" }}
          />
        </label>

        <label>
          High:
          <input
            name="High"
            type="number"
            placeholder="Enter High price"
            value={form.High}
            onChange={handleChange}
            style={{ width: "100%", padding: "8px", margin: "8px 0" }}
          />
        </label>

        <label>
          Low:
          <input
            name="Low"
            type="number"
            placeholder="Enter Low price"
            value={form.Low}
            onChange={handleChange}
            style={{ width: "100%", padding: "8px", margin: "8px 0" }}
          />
        </label>

        <label>
          Volume:
          <input
            name="Volume"
            type="number"
            placeholder="Enter Volume"
            value={form.Volume}
            onChange={handleChange}
            style={{ width: "100%", padding: "8px", margin: "8px 0" }}
          />
        </label>

        <button
          type="submit"
          style={{
            width: "100%",
            padding: "10px",
            marginTop: "15px",
            backgroundColor: "#4CAF50",
            color: "white",
            fontSize: "16px",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Predict
        </button>
      </form>

      {/* Prediction */}
      {prediction !== null && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            backgroundColor: "#e6ffed",
            border: "1px solid #b2f5bf",
            borderRadius: "6px",
            textAlign: "center",
            fontWeight: "bold",
          }}
        >
          Predicted Close Price: {prediction.toLocaleString()}
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            backgroundColor: "#ffe6e6",
            border: "1px solid #f5b2b2",
            borderRadius: "6px",
            color: "#d8000c",
            textAlign: "center",
            fontWeight: "bold",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}

export default App;
