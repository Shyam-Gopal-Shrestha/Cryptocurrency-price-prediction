// src/components/PredictionForm.jsx
import React, { useEffect, useState } from "react";
import api from "../api/axios";

export default function PredictionForm() {
  const [form, setForm] = useState({
    symbol: "BTC-USD",
    model: "linear_regression",
    date: "",
    Open: "",
    High: "",
    Low: "",
    Volume: "",
  });

  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [autofillLoading, setAutofillLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  useEffect(() => {
    // Reset date and OHLCV fields when crypto symbol changes.
    setForm((prev) => ({
      ...prev,
      date: "",
      Open: "",
      High: "",
      Low: "",
      Volume: "",
    }));
  }, [form.symbol]);

  const handleAutofill = async () => {
    if (!form.date) {
      setError("Please select a date first.");
      return;
    }

    setError("");
    setAutofillLoading(true);
    try {
      const res = await api.get("/historical", {
        params: { symbol: form.symbol, date: form.date },
      });

      const data = res.data;
      if (data?.error) {
        setError(data.error);
        return;
      }

      setForm((prev) => ({
        ...prev,
        Open: String(data.Open ?? ""),
        High: String(data.High ?? ""),
        Low: String(data.Low ?? ""),
        Volume: String(data.Volume ?? ""),
      }));
    } catch (err) {
      setError(
        "Failed to autofill values: " +
          (err.response?.data?.detail || err.message),
      );
    } finally {
      setAutofillLoading(false);
    }
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    setLoading(true);
    setPrediction(null);
    setError("");

    const payload = {
      symbol: form.symbol,
      model: form.model,
      Open: parseFloat(form.Open),
      High: parseFloat(form.High),
      Low: parseFloat(form.Low),
      Volume: parseFloat(form.Volume),
    };

    if (
      [payload.Open, payload.High, payload.Low, payload.Volume].some((v) =>
        Number.isNaN(v),
      )
    ) {
      setError("Please fill all fields with valid numbers.");
      setLoading(false);
      return;
    }

    try {
      const res = await api.post("/predict", payload);
      setPrediction(res.data.prediction ?? res.data);
    } catch (err) {
      console.error(err);
      setError(
        "Prediction failed: " + (err.response?.data?.detail || err.message),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handlePredict} style={{ marginBottom: "20px" }}>
        <label>Crypto:</label>
        <select name="symbol" value={form.symbol} onChange={handleChange}>
          <option value="BTC-USD">Bitcoin</option>
          <option value="ETH-USD">Ethereum</option>
          <option value="SOL-USD">Solana</option>
          <option value="ADA-USD">Cardano</option>
        </select>
        <br />
        <br />

        <label>Model:</label>
        <select name="model" value={form.model} onChange={handleChange}>
          <option value="linear_regression">Linear Regression</option>
          <option value="random_forest">Random Forest</option>
          <option value="xgboost">XGBoost</option>
          <option value="svr">SVR</option>
          <option value="lstm">LSTM</option>
        </select>
        <br />
        <br />

        <label>Date:</label>
        <input
          type="date"
          name="date"
          value={form.date}
          onChange={handleChange}
          required
        />
        <button
          type="button"
          onClick={handleAutofill}
          style={{ marginLeft: "8px" }}
        >
          {autofillLoading ? "Loading..." : "Auto Fill"}
        </button>
        <br />
        <br />

        <label>Open:</label>
        <input
          type="number"
          name="Open"
          value={form.Open}
          onChange={handleChange}
          step="any"
          required
        />
        <br />
        <br />

        <label>High:</label>
        <input
          type="number"
          name="High"
          value={form.High}
          onChange={handleChange}
          step="any"
          required
        />
        <br />
        <br />

        <label>Low:</label>
        <input
          type="number"
          name="Low"
          value={form.Low}
          onChange={handleChange}
          step="any"
          required
        />
        <br />
        <br />

        <label>Volume:</label>
        <input
          type="number"
          name="Volume"
          value={form.Volume}
          onChange={handleChange}
          step="any"
          required
        />
        <br />
        <br />

        <button type="submit">{loading ? "Predicting..." : "Predict"}</button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {prediction !== null && (
        <div style={{ fontWeight: "bold", marginTop: "10px" }}>
          Predicted Close Price: {Number(prediction).toLocaleString()}
        </div>
      )}
    </div>
  );
}
