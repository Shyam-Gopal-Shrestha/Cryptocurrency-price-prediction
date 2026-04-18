import React, { useContext, useEffect, useMemo, useState } from "react";
import api from "../../api/axios";
import { AuthContext } from "../../context/AuthContext";
import { Line } from "react-chartjs-2";
import { LogOut } from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import QRCode from "qrcode";
import "./DashboardSuite.css";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
);

export default function UserDashboard() {
  const { logout } = useContext(AuthContext);
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [config, setConfig] = useState({
    cryptocurrencies: [],
    max_horizon: 30,
  });
  const [form, setForm] = useState({
    symbol: "BTC-USD",
    horizon: 1,
    explanation_mode: "simple",
    risk_tolerance: "medium",
  });
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [profile, setProfile] = useState(null);
  const [setup2FA, setSetup2FA] = useState(null);
  const [otpCode, setOtpCode] = useState("");

  const [liveSeries, setLiveSeries] = useState([]);
  const [livePrice, setLivePrice] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState("");
  const [liveRange, setLiveRange] = useState("1");
  const [liveSource, setLiveSource] = useState("proxy");

  const [twoFASetup, setTwoFASetup] = useState(null); // expected: { secret, otpauth_uri }
  const [qrDataUrl, setQrDataUrl] = useState("");

  const menuItems = [
    { key: "dashboard", label: "Dashboard" },
    { key: "predict", label: "Predict Price" },
    { key: "live", label: "Live Chart" },
    { key: "history", label: "History" },
    { key: "profile", label: "Profile" },
    { key: "security", label: "Security" },
  ];

  const loadConfigAndHistory = async () => {
    setError("");
    setSuccess("");
    try {
      const [cfg, hist] = await Promise.all([
        api.get("/user/config"),
        api.get("/user/predictions/history"),
      ]);
      const nextConfig = cfg.data || { cryptocurrencies: [], max_horizon: 30 };
      setConfig(nextConfig);
      setHistory(hist.data || []);
      const first = nextConfig.cryptocurrencies?.[0]?.symbol || "BTC-USD";
      setForm((prev) => ({
        ...prev,
        symbol: first,
      }));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load dashboard data.");
    }
  };

  useEffect(() => {
    loadConfigAndHistory();
  }, []);

  const loadProfile = async () => {
    try {
      const me = await api.get("/auth/me");
      setProfile(me.data || null);
    } catch {
      // keep profile optional
    }
  };

  useEffect(() => {
    if (activeMenu === "profile" || activeMenu === "security") {
      loadProfile();
    }
  }, [activeMenu]);

  const trendColor = useMemo(() => {
    if (!prediction) return "#334155";
    return prediction.trend === "bullish" ? "#16a34a" : "#dc2626";
  }, [prediction]);

  const historyChartData = useMemo(() => {
    const points = [...history].reverse().slice(-20);
    return {
      labels: points.map((p) => {
        const d = new Date(p.created_at);
        return Number.isNaN(d.getTime())
          ? p.created_at
          : d.toLocaleDateString();
      }),
      datasets: [
        {
          label: "Predicted Price",
          data: points.map((p) => p.predicted_price),
          borderColor: "#2563eb",
          backgroundColor: "rgba(37,99,235,0.2)",
          tension: 0.25,
          fill: true,
        },
      ],
    };
  }, [history]);

  const liveChartData = useMemo(() => {
    return {
      labels: liveSeries.map((p) => {
        const d = new Date(p.time);
        return d.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      }),
      datasets: [
        {
          label: `${form.symbol} live price (USD)`,
          data: liveSeries.map((p) => p.price),
          borderColor: "#16a34a",
          backgroundColor: "rgba(22,163,74,0.18)",
          tension: 0.22,
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    };
  }, [liveSeries, form.symbol]);

  const fetchLiveChart = async () => {
    setLiveLoading(true);
    setLiveError("");
    try {
      const res = await api.get("/api/live-market", {
        params: {
          symbol: form.symbol,
          days: Number(liveRange),
        },
      });

      const points = Array.isArray(res.data?.prices) ? res.data.prices : [];
      setLiveSeries(points);
      setLivePrice(res.data?.current_price ?? null);
      setLiveSource(res.data?.source || "proxy");
    } catch (err) {
      setLiveError(
        err.response?.data?.detail ||
          "Live price feed is currently unavailable. Try again shortly.",
      );
    } finally {
      setLiveLoading(false);
    }
  };

  useEffect(() => {
    if (activeMenu !== "dashboard" && activeMenu !== "live") return;

    fetchLiveChart();
    const intervalId = setInterval(fetchLiveChart, 60000);
    return () => clearInterval(intervalId);
  }, [activeMenu, form.symbol, liveRange]);

  const submitPrediction = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const res = await api.post("/user/predict", {
        symbol: form.symbol,
        horizon: Number(form.horizon),
        explanation_mode: form.explanation_mode,
      });
      setPrediction(res.data);
      setSuccess("Prediction generated successfully.");
      const hist = await api.get("/user/predictions/history");
      setHistory(hist.data || []);
      setActiveMenu("dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Prediction failed.");
    } finally {
      setLoading(false);
    }
  };

  const setupTwoFactor = async () => {
    setError("");
    setSuccess("");
    try {
      const res = await api.post("/auth/2fa/setup");
      const data = res.data || null;
      setSetup2FA(data);
      setTwoFASetup(data); // ← also set twoFASetup so QR renders
      setSuccess("2FA secret generated. Verify code to enable.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to setup 2FA.");
    }
  };

  const enableTwoFactor = async () => {
    setError("");
    setSuccess("");
    try {
      await api.post("/auth/2fa/enable", { otp_code: otpCode });
      setSuccess("Two-factor authentication enabled.");
      setOtpCode("");
      await loadProfile();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to enable 2FA.");
    }
  };

  const disableTwoFactor = async () => {
    setError("");
    setSuccess("");
    try {
      await api.post("/auth/2fa/disable");
      setSuccess("Two-factor authentication disabled.");
      setSetup2FA(null);
      await loadProfile();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to disable 2FA.");
    }
  };

  const handleGenerate2FA = async () => {
    setError("");
    setSuccess("");
    try {
      const res = await api.post("/auth/2fa/setup");
      setTwoFASetup(res.data || null);
      setSuccess("2FA secret generated. Verify code to enable.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to setup 2FA.");
    }
  };

  useEffect(() => {
    let mounted = true;
    const uri = twoFASetup?.otpauth_uri || twoFASetup?.otpauth_url;

    const buildQr = async () => {
      if (!uri) {
        setQrDataUrl("");
        return;
      }
      try {
        const url = await QRCode.toDataURL(uri, { width: 220, margin: 1 });
        if (mounted) setQrDataUrl(url);
      } catch {
        if (mounted) setQrDataUrl("");
      }
    };

    buildQr();
    return () => {
      mounted = false;
    };
  }, [twoFASetup?.otpauth_uri, twoFASetup?.otpauth_url]);

  return (
    <div className="dash-layout">
      <aside className="dash-sidebar">
        <div>
          <div className="dash-brand">
            <span className="dash-brand-dot" />
            <h2>User Space</h2>
          </div>
          <p className="dash-subtitle">Prediction assistant and history</p>
        </div>

        <div className="dash-menu">
          {menuItems.map((item) => (
            <button
              key={item.key}
              className={`dash-menu-btn ${activeMenu === item.key ? "active" : ""}`}
              onClick={() => setActiveMenu(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <button
          className="dash-menu-btn dash-logout-btn"
          onClick={logout}
          type="button"
        >
          <LogOut size={15} style={{ marginRight: 6 }} />
          Sign out
        </button>
      </aside>

      <main className="dash-main">
        <div className="dash-topbar">
          <div>
            <h1>User Dashboard</h1>
            <p>
              Choose a crypto, set timeframe, and get AI-assisted explanation.
            </p>
          </div>
          <span className="dash-chip">
            {loading ? "Predicting..." : "Ready"}
          </span>
        </div>

        {error && <div className="dash-alert error">{error}</div>}
        {success && <div className="dash-alert success">{success}</div>}

        {(activeMenu === "dashboard" || activeMenu === "predict") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Prediction Module</h3>
            <form onSubmit={submitPrediction}>
              <div className="dash-form-grid">
                <div className="dash-form-row">
                  <label>Cryptocurrency</label>
                  <select
                    className="dash-select"
                    value={form.symbol}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, symbol: e.target.value }))
                    }
                  >
                    {config.cryptocurrencies.map((crypto) => (
                      <option key={crypto.symbol} value={crypto.symbol}>
                        {crypto.name} ({crypto.symbol})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="dash-form-row">
                  <label>Timeframe (days)</label>
                  <input
                    className="dash-input"
                    type="number"
                    min={1}
                    max={config.max_horizon || 30}
                    value={form.horizon}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, horizon: e.target.value }))
                    }
                  />
                </div>

                <div className="dash-form-row">
                  <label>Explanation mode</label>
                  <select
                    className="dash-select"
                    value={form.explanation_mode}
                    onChange={(e) =>
                      setForm((p) => ({
                        ...p,
                        explanation_mode: e.target.value,
                      }))
                    }
                  >
                    <option value="simple">Simple</option>
                    <option value="technical">Technical</option>
                  </select>
                </div>

                <div className="dash-form-row">
                  <label>Risk tolerance (optional)</label>
                  <select
                    className="dash-select"
                    value={form.risk_tolerance}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, risk_tolerance: e.target.value }))
                    }
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <button
                className="dash-btn primary"
                type="submit"
                style={{ marginTop: 10 }}
              >
                {loading ? "Generating..." : "Generate prediction"}
              </button>
            </form>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "predict") &&
          prediction && (
            <section className="dash-grid-2" style={{ marginBottom: 12 }}>
              <div className="dash-card">
                <h3>Prediction Card</h3>
                <p>
                  <strong>Predicted Price:</strong> $
                  {Number(prediction.predicted_price || 0).toFixed(2)}
                </p>
                <p>
                  <strong>Trend:</strong>{" "}
                  <span style={{ color: trendColor, fontWeight: 700 }}>
                    {prediction.trend}
                  </span>
                </p>
                <p>
                  <strong>Confidence:</strong>{" "}
                  {Number(prediction.confidence || 0).toFixed(1)}%
                </p>
                <p>
                  <strong>Model:</strong> {prediction.model}
                </p>
                <p>
                  <strong>Last Close:</strong> $
                  {Number(prediction.last_close || 0).toFixed(2)}
                </p>
              </div>

              <div className="dash-card">
                <h3>Explanation Card (Gemini/Internal)</h3>
                <p style={{ lineHeight: 1.6 }}>{prediction.explanation}</p>
              </div>
            </section>
          )}

        {(activeMenu === "dashboard" || activeMenu === "live") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Live Price Chart</h3>
            <div className="dash-actions" style={{ marginBottom: 10 }}>
              <select
                className="dash-select"
                style={{ maxWidth: 220 }}
                value={liveRange}
                onChange={(e) => setLiveRange(e.target.value)}
              >
                <option value="1">Last 24h</option>
                <option value="7">Last 7 days</option>
                <option value="30">Last 30 days</option>
              </select>
              <button className="dash-btn neutral" onClick={fetchLiveChart}>
                Refresh live chart
              </button>
            </div>

            <p className="dash-stat-label" style={{ marginBottom: 10 }}>
              Source: {liveSource} (via backend proxy) · Symbol: {form.symbol}
            </p>

            {livePrice !== null && (
              <p
                style={{
                  margin: "0 0 10px",
                  fontWeight: 700,
                  color: "#0f172a",
                }}
              >
                Current Price: ${Number(livePrice).toLocaleString()}
              </p>
            )}

            {liveError && <div className="dash-alert error">{liveError}</div>}

            {liveLoading && liveSeries.length === 0 ? (
              <p>Loading live market chart...</p>
            ) : liveSeries.length > 0 ? (
              <div style={{ maxWidth: 980 }}>
                <Line
                  data={liveChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { position: "top" } },
                    scales: {
                      y: {
                        ticks: {
                          callback: (value) =>
                            `$${Number(value).toLocaleString()}`,
                        },
                      },
                    },
                  }}
                />
              </div>
            ) : (
              <p>No live data points available.</p>
            )}
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "history") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Historical Predictions</h3>
            {history.length > 0 ? (
              <div style={{ maxWidth: 900, marginBottom: 12 }}>
                <Line
                  data={historyChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { position: "top" } },
                  }}
                />
              </div>
            ) : (
              <p>No prediction history yet.</p>
            )}

            <div className="dash-table-wrap">
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Symbol</th>
                    <th>Horizon</th>
                    <th>Predicted Price</th>
                    <th>Trend</th>
                    <th>Confidence</th>
                    <th>Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan={7}>No history records.</td>
                    </tr>
                  ) : (
                    history.map((item) => (
                      <tr key={item.id}>
                        <td>{item.created_at}</td>
                        <td>{item.symbol}</td>
                        <td>{item.horizon}</td>
                        <td>${Number(item.predicted_price || 0).toFixed(2)}</td>
                        <td>{item.trend}</td>
                        <td>{Number(item.confidence || 0).toFixed(1)}%</td>
                        <td>{item.explanation_mode}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeMenu === "profile" && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Profile</h3>
            {!profile ? (
              <p>Unable to load profile details.</p>
            ) : (
              <div className="dash-grid-2">
                <div>
                  <p>
                    <strong>Email:</strong> {profile.email}
                  </p>
                  <p>
                    <strong>Role:</strong> {profile.role}
                  </p>
                  <p>
                    <strong>Status:</strong> {profile.status}
                  </p>
                </div>
                <div>
                  <p>
                    <strong>2FA Enabled:</strong>{" "}
                    {profile.twofa_enabled ? "Yes" : "No"}
                  </p>
                  <p>
                    <strong>User ID:</strong> {profile.id}
                  </p>
                </div>
              </div>
            )}
          </section>
        )}

        {activeMenu === "security" && (
          <section className="dash-card">
            <h3>Security & Two-Factor Authentication</h3>
            <div className="dash-actions" style={{ marginBottom: 10 }}>
              <button className="dash-btn primary" onClick={setupTwoFactor}>
                Generate 2FA Secret
              </button>
              <button className="dash-btn danger" onClick={disableTwoFactor}>
                Disable 2FA
              </button>
            </div>

            {setup2FA && (
              <div className="dash-card" style={{ marginBottom: 10 }}>
                <p>
                  <strong>Secret:</strong> {setup2FA.secret}
                </p>
                <p>
                  <strong>OTP Auth URL:</strong>{" "}
                  {setup2FA.otpauth_uri || setup2FA.otpauth_url}
                </p>
              </div>
            )}

            <div className="dash-form-row" style={{ maxWidth: 280 }}>
              <label>Enter OTP code to enable 2FA</label>
              <input
                className="dash-input"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                placeholder="6-digit code"
              />
            </div>
            <button
              className="dash-btn success"
              onClick={enableTwoFactor}
              style={{ marginTop: 10 }}
            >
              Enable 2FA
            </button>

            {twoFASetup &&
              (twoFASetup.otpauth_uri || twoFASetup.otpauth_url) && (
                <div style={{ marginTop: 12 }}>
                  <p style={{ marginBottom: 8, fontWeight: 600 }}>
                    Scan QR in Microsoft Authenticator
                  </p>
                  {qrDataUrl ? (
                    <img
                      src={qrDataUrl}
                      alt="2FA QR Code"
                      width={220}
                      height={220}
                      style={{
                        borderRadius: 10,
                        border: "1px solid #e5e7eb",
                        background: "#fff",
                        padding: 8,
                      }}
                    />
                  ) : (
                    <p>Generating QR...</p>
                  )}
                  <p style={{ marginTop: 10 }}>
                    <strong>Secret:</strong> {twoFASetup.secret}
                  </p>
                </div>
              )}
          </section>
        )}
      </main>
    </div>
  );
}
