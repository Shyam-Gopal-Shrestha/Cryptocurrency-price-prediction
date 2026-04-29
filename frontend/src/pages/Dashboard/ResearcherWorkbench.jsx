import React, { useContext, useEffect, useMemo, useState } from "react";
import api from "../../api/axios";
import { AuthContext } from "../../context/AuthContext";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import "./DashboardSuite.css";
import { LogOut } from "lucide-react";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

export default function ResearcherWorkbench() {
  const { logout, user } = useContext(AuthContext);
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [config, setConfig] = useState({ cryptocurrencies: [], models: [] });
  const [experiments, setExperiments] = useState([]);
  const [status, setStatus] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [fetchForm, setFetchForm] = useState({
    symbol: "BTC-USD",
    start_date: "2021-01-01",
    end_date: new Date().toISOString().slice(0, 10),
    interval: "1d",
  });

  const [preprocessForm, setPreprocessForm] = useState({
    symbol: "BTC-USD",
    fast_window: 7,
    slow_window: 21,
  });
  const [preprocessPreview, setPreprocessPreview] = useState([]);

  const [trainForm, setTrainForm] = useState({
    symbol: "BTC-USD",
    models: ["linear_regression", "random_forest", "xgboost"],
    horizon: 1,
    test_size: 0.2,
    auto_deploy_best: true,
  });
  const [trainResult, setTrainResult] = useState(null);

  const menuItems = [
    { key: "dashboard", label: "Dashboard" },
    { key: "fetch", label: "Fetch Data" },
    { key: "preprocess", label: "Preprocessing" },
    { key: "train", label: "Train Model" },
    { key: "evaluate", label: "Evaluate Model" },
    { key: "compare", label: "Compare Models" },
    { key: "deploy", label: "Deploy Model" },
    { key: "experiments", label: "Experiments" },
  ];

  const loadInitial = async () => {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const [cfg, exps] = await Promise.all([
        api.get("/researcher/config"),
        api.get("/researcher/experiments"),
      ]);

      const nextConfig = cfg.data || { cryptocurrencies: [], models: [] };
      const nextExperiments = exps.data || [];
      setConfig(nextConfig);
      setExperiments(nextExperiments);

      const defaultSymbol =
        nextConfig.cryptocurrencies?.[0]?.symbol || "BTC-USD";
      setFetchForm((p) => ({ ...p, symbol: defaultSymbol }));
      setPreprocessForm((p) => ({ ...p, symbol: defaultSymbol }));
      setTrainForm((p) => ({
        ...p,
        symbol: defaultSymbol,
        models:
          nextConfig.models?.length > 0
            ? nextConfig.models.slice(0, 3)
            : ["linear_regression", "random_forest"],
      }));
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to load researcher workspace.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitial();
  }, []);

  const deployed = useMemo(
    () => experiments.filter((e) => e.is_deployed),
    [experiments],
  );

  const bestByRmse = useMemo(() => {
    const trained = experiments.filter((e) => e.metrics?.rmse !== undefined);
    if (trained.length === 0) return null;
    return [...trained].sort((a, b) => a.metrics.rmse - b.metrics.rmse)[0];
  }, [experiments]);

  const researcherDisplayName = useMemo(() => {
    const raw = user?.full_name || user?.name || user?.email || "";
    if (!raw) return "Researcher";
    const localPart = raw.includes("@") ? raw.split("@")[0] : raw;
    return localPart
      .replace(/[._-]+/g, " ")
      .split(" ")
      .filter(Boolean)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }, [user]);

  const comparisonData = useMemo(() => {
    const labels = experiments.map((e) => `#${e.id} ${e.model_name}`);
    const rmse = experiments.map((e) => e.metrics?.rmse ?? null);
    const mae = experiments.map((e) => e.metrics?.mae ?? null);

    return {
      labels,
      datasets: [
        {
          label: "RMSE",
          data: rmse,
          backgroundColor: "rgba(37,99,235,0.7)",
          borderRadius: 6,
        },
        {
          label: "MAE",
          data: mae,
          backgroundColor: "rgba(16,185,129,0.7)",
          borderRadius: 6,
        },
      ],
    };
  }, [experiments]);

  const fetchData = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setStatus("Fetching historical data from Yahoo Finance...");
    try {
      const res = await api.post("/researcher/fetch-data", fetchForm);
      setSuccess(res.data?.message || "Historical data fetched.");
      setStatus("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch data.");
      setStatus("");
    }
  };

  const preprocessData = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setStatus("Running preprocessing and feature engineering...");
    try {
      const res = await api.post("/researcher/preprocess", {
        ...preprocessForm,
        fast_window: Number(preprocessForm.fast_window),
        slow_window: Number(preprocessForm.slow_window),
      });
      setPreprocessPreview(res.data?.preview || []);
      setSuccess(
        `Preprocess complete. Removed ${res.data?.missing_values_removed ?? 0} rows with missing values.`,
      );
      setStatus("");
    } catch (err) {
      setError(err.response?.data?.detail || "Preprocessing failed.");
      setStatus("");
    }
  };

  const toggleModel = (modelName) => {
    setTrainForm((prev) => {
      const exists = prev.models.includes(modelName);
      if (exists) {
        return { ...prev, models: prev.models.filter((m) => m !== modelName) };
      }
      return { ...prev, models: [...prev.models, modelName] };
    });
  };

  const trainModels = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setStatus("Training selected models...");
    setTrainResult(null);

    if (trainForm.models.length === 0) {
      setError("Select at least one model.");
      setStatus("");
      return;
    }

    try {
      const payload = {
        ...trainForm,
        horizon: Number(trainForm.horizon),
        test_size: Number(trainForm.test_size),
      };
      const res = await api.post("/researcher/train", payload);
      setTrainResult(res.data || null);
      setSuccess("Training complete.");
      setStatus("");
      await loadInitial();
    } catch (err) {
      setError(err.response?.data?.detail || "Training failed.");
      setStatus("");
    }
  };

  const deployExperiment = async (experimentId) => {
    setError("");
    setSuccess("");
    try {
      const res = await api.post(`/researcher/deploy/${experimentId}`);
      setSuccess(res.data?.message || "Model deployed.");
      await loadInitial();
    } catch (err) {
      setError(err.response?.data?.detail || "Deploy failed.");
    }
  };

  const [pvActual, setPvActual] = useState(null);
  const [pvModel, setPvModel] = useState("random_forest");
  const [pvSymbol, setPvSymbol] = useState("BTC-USD");
  const [pvLoading, setPvLoading] = useState(false);
  const [pvError, setPvError] = useState("");

  const [expSymbolFilter, setExpSymbolFilter] = useState("all");
  const [expModelFilter, setExpModelFilter] = useState("all");
  const [expStatusFilter, setExpStatusFilter] = useState("all");

  const loadPredictionVsActual = async () => {
    setPvLoading(true);
    setPvError("");
    try {
      const res = await api.get("/prediction-vs-actual", {
        params: {
          symbol: pvSymbol,
          model: pvModel,
          limit: 60,
        },
      });
      setPvActual(res.data);
    } catch (err) {
      setPvActual(null);
      setPvError(
        err.response?.data?.detail ||
          "Failed to load prediction vs actual data.",
      );
    } finally {
      setPvLoading(false);
    }
  };

  const pvChartData = pvActual
    ? {
        labels: pvActual.points.map((p) => p.date),
        datasets: [
          {
            label: "Actual",
            data: pvActual.points.map((p) => p.actual),
            borderColor: "#2563eb",
            tension: 0.25,
          },
          {
            label: "Predicted",
            data: pvActual.points.map((p) => p.predicted),
            borderColor: "#f59e0b",
            tension: 0.25,
          },
        ],
      }
    : null;

  const filteredExperiments = useMemo(() => {
    return experiments.filter((exp) => {
      const symbolOk =
        expSymbolFilter === "all" || exp.symbol === expSymbolFilter;
      const modelOk =
        expModelFilter === "all" || exp.model_name === expModelFilter;
      const deployLabel = exp.is_deployed
        ? "deployed"
        : String(exp.status || "").toLowerCase();
      const statusOk =
        expStatusFilter === "all" || deployLabel === expStatusFilter;
      return symbolOk && modelOk && statusOk;
    });
  }, [experiments, expModelFilter, expStatusFilter, expSymbolFilter]);

  const bestFilteredByRmse = useMemo(() => {
    const trained = filteredExperiments.filter(
      (e) => e.metrics?.rmse !== undefined && e.metrics?.rmse !== null,
    );
    if (!trained.length) return null;
    return [...trained].sort(
      (a, b) => Number(a.metrics.rmse) - Number(b.metrics.rmse),
    )[0];
  }, [filteredExperiments]);

  const deployBestFiltered = async () => {
    if (!bestFilteredByRmse) {
      setError("No filtered experiment with RMSE is available.");
      return;
    }
    if (
      !window.confirm(
        `Deploy best filtered model #${bestFilteredByRmse.id} (${bestFilteredByRmse.model_name})?`,
      )
    ) {
      return;
    }
    await deployExperiment(bestFilteredByRmse.id);
  };

  return (
    <div className="dash-layout">
      <aside className="dash-sidebar">
        <div>
          <div className="dash-brand">
            <span className="dash-brand-dot" />
            <h2>Researcher</h2>
          </div>
          <p className="dash-subtitle">Model training & analysis</p>

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
            <h1>Welcome, {researcherDisplayName}</h1>
            <p>
              Fetch, preprocess, train, evaluate, and deploy forecasting models.
            </p>
          </div>
          <span className="dash-chip">{loading ? "Loading" : "Ready"}</span>
        </div>

        {status && <div className="dash-alert success">{status}</div>}
        {success && <div className="dash-alert success">{success}</div>}
        {error && <div className="dash-alert error">{error}</div>}

        {(activeMenu === "dashboard" || activeMenu === "fetch") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Data Fetch Panel (Yahoo Finance)</h3>
            <form onSubmit={fetchData}>
              <div className="dash-form-grid">
                <div className="dash-form-row">
                  <label>Cryptocurrency</label>
                  <select
                    className="dash-select"
                    value={fetchForm.symbol}
                    onChange={(e) =>
                      setFetchForm((p) => ({ ...p, symbol: e.target.value }))
                    }
                  >
                    {config.cryptocurrencies.map((c) => (
                      <option key={c.symbol} value={c.symbol}>
                        {c.name} ({c.symbol})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="dash-form-row">
                  <label>Interval</label>
                  <select
                    className="dash-select"
                    value={fetchForm.interval}
                    onChange={(e) =>
                      setFetchForm((p) => ({ ...p, interval: e.target.value }))
                    }
                  >
                    <option value="1d">1 day</option>
                    <option value="1h">1 hour</option>
                    <option value="1wk">1 week</option>
                  </select>
                </div>
                <div className="dash-form-row">
                  <label>Start date</label>
                  <input
                    className="dash-input"
                    type="date"
                    value={fetchForm.start_date}
                    onChange={(e) =>
                      setFetchForm((p) => ({
                        ...p,
                        start_date: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="dash-form-row">
                  <label>End date</label>
                  <input
                    className="dash-input"
                    type="date"
                    value={fetchForm.end_date}
                    onChange={(e) =>
                      setFetchForm((p) => ({ ...p, end_date: e.target.value }))
                    }
                  />
                </div>
              </div>
              <button
                className="dash-btn primary"
                type="submit"
                style={{ marginTop: 10 }}
              >
                Fetch and store data
              </button>
            </form>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "preprocess") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Feature Engineering Panel</h3>
            <form onSubmit={preprocessData}>
              <div className="dash-form-grid">
                <div className="dash-form-row">
                  <label>Cryptocurrency</label>
                  <select
                    className="dash-select"
                    value={preprocessForm.symbol}
                    onChange={(e) =>
                      setPreprocessForm((p) => ({
                        ...p,
                        symbol: e.target.value,
                      }))
                    }
                  >
                    {config.cryptocurrencies.map((c) => (
                      <option key={c.symbol} value={c.symbol}>
                        {c.name} ({c.symbol})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="dash-form-row">
                  <label>Fast MA window</label>
                  <input
                    className="dash-input"
                    type="number"
                    min={2}
                    value={preprocessForm.fast_window}
                    onChange={(e) =>
                      setPreprocessForm((p) => ({
                        ...p,
                        fast_window: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="dash-form-row">
                  <label>Slow MA window</label>
                  <input
                    className="dash-input"
                    type="number"
                    min={3}
                    value={preprocessForm.slow_window}
                    onChange={(e) =>
                      setPreprocessForm((p) => ({
                        ...p,
                        slow_window: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>
              <button
                className="dash-btn primary"
                type="submit"
                style={{ marginTop: 10 }}
              >
                Run preprocessing
              </button>
            </form>

            <div className="dash-table-wrap" style={{ marginTop: 14 }}>
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Close</th>
                    <th>MA Fast</th>
                    <th>MA Slow</th>
                    <th>RSI</th>
                    <th>MACD</th>
                    <th>Volatility</th>
                  </tr>
                </thead>
                <tbody>
                  {preprocessPreview.length === 0 ? (
                    <tr>
                      <td colSpan={7}>No preview rows yet.</td>
                    </tr>
                  ) : (
                    preprocessPreview.map((row, idx) => (
                      <tr key={`${row.timestamp}-${idx}`}>
                        <td>{row.timestamp}</td>
                        <td>{row.close}</td>
                        <td>{row.ma_fast}</td>
                        <td>{row.ma_slow}</td>
                        <td>{row.rsi}</td>
                        <td>{row.macd}</td>
                        <td>{row.volatility}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "train") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Model Training Panel</h3>
            <form onSubmit={trainModels}>
              <div className="dash-form-grid">
                <div className="dash-form-row">
                  <label>Cryptocurrency</label>
                  <select
                    className="dash-select"
                    value={trainForm.symbol}
                    onChange={(e) =>
                      setTrainForm((p) => ({ ...p, symbol: e.target.value }))
                    }
                  >
                    {config.cryptocurrencies.map((c) => (
                      <option key={c.symbol} value={c.symbol}>
                        {c.name} ({c.symbol})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="dash-form-row">
                  <label>Prediction horizon (days)</label>
                  <input
                    className="dash-input"
                    type="number"
                    min={1}
                    max={30}
                    value={trainForm.horizon}
                    onChange={(e) =>
                      setTrainForm((p) => ({ ...p, horizon: e.target.value }))
                    }
                  />
                </div>
                <div className="dash-form-row">
                  <label>Test size</label>
                  <input
                    className="dash-input"
                    type="number"
                    min={0.05}
                    max={0.49}
                    step={0.01}
                    value={trainForm.test_size}
                    onChange={(e) =>
                      setTrainForm((p) => ({ ...p, test_size: e.target.value }))
                    }
                  />
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                <p className="dash-stat-label" style={{ marginBottom: 6 }}>
                  Select models to train
                </p>
                <div className="dash-actions">
                  {config.models.map((m) => {
                    const selected = trainForm.models.includes(m);
                    return (
                      <button
                        key={m}
                        type="button"
                        className={`dash-btn ${selected ? "primary" : "neutral"}`}
                        onClick={() => toggleModel(m)}
                      >
                        {m}
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="dash-switch" style={{ marginTop: 10 }}>
                <input
                  type="checkbox"
                  checked={trainForm.auto_deploy_best}
                  onChange={(e) =>
                    setTrainForm((p) => ({
                      ...p,
                      auto_deploy_best: e.target.checked,
                    }))
                  }
                />
                Auto-deploy best model by RMSE
              </label>

              <button
                className="dash-btn primary"
                type="submit"
                style={{ marginTop: 10 }}
              >
                Train selected models
              </button>
            </form>

            {trainResult?.best_model && (
              <div className="dash-card" style={{ marginTop: 14 }}>
                <h3>Best model result</h3>
                <p>
                  <strong>Model:</strong> {trainResult.best_model.model}
                </p>
                <p>
                  <strong>Experiment ID:</strong>{" "}
                  {trainResult.best_model.experiment_id}
                </p>
                <p>
                  <strong>RMSE:</strong>{" "}
                  {trainResult.best_model.metrics?.rmse ?? "-"}
                </p>
                <p>
                  <strong>MAE:</strong>{" "}
                  {trainResult.best_model.metrics?.mae ?? "-"}
                </p>
                <p>
                  <strong>MAPE:</strong>{" "}
                  {trainResult.best_model.metrics?.mape ?? "-"}
                </p>
                <p>
                  <strong>R²:</strong>{" "}
                  {trainResult.best_model.metrics?.r2 ?? "-"}
                </p>
              </div>
            )}
          </section>
        )}

        {(activeMenu === "dashboard" ||
          activeMenu === "compare" ||
          activeMenu === "evaluate") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Model Evaluation & Comparison</h3>

            {bestByRmse && (
              <p style={{ marginBottom: 10 }}>
                Current best model: <strong>{bestByRmse.model_name}</strong>{" "}
                (Experiment #{bestByRmse.id}, RMSE {bestByRmse.metrics?.rmse})
              </p>
            )}

            {experiments.length > 0 ? (
              <div style={{ maxWidth: 920 }}>
                <Bar
                  data={comparisonData}
                  options={{
                    responsive: true,
                    plugins: { legend: { position: "top" } },
                  }}
                />
              </div>
            ) : (
              <p>No experiments available yet.</p>
            )}
          </section>
        )}

        {(activeMenu === "dashboard" ||
          activeMenu === "deploy" ||
          activeMenu === "experiments") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Experiments & Deployment Control</h3>
            <p className="dash-stat-label" style={{ marginBottom: 10 }}>
              Deployed models: {deployed.length}
            </p>

            <div className="dash-toolbar">
              <span className="dash-kpi-pill">
                Matched: {filteredExperiments.length}
              </span>
              <span className="dash-kpi-pill">
                Best RMSE: {bestFilteredByRmse?.metrics?.rmse ?? "-"}
              </span>
              <select
                className="dash-select"
                style={{ maxWidth: 220 }}
                value={expSymbolFilter}
                onChange={(e) => setExpSymbolFilter(e.target.value)}
              >
                <option value="all">All symbols</option>
                {Array.from(new Set(experiments.map((e) => e.symbol))).map(
                  (symbol) => (
                    <option key={symbol} value={symbol}>
                      {symbol}
                    </option>
                  ),
                )}
              </select>
              <select
                className="dash-select"
                style={{ maxWidth: 220 }}
                value={expModelFilter}
                onChange={(e) => setExpModelFilter(e.target.value)}
              >
                <option value="all">All models</option>
                {Array.from(new Set(experiments.map((e) => e.model_name))).map(
                  (modelName) => (
                    <option key={modelName} value={modelName}>
                      {modelName}
                    </option>
                  ),
                )}
              </select>
              <select
                className="dash-select"
                style={{ maxWidth: 220 }}
                value={expStatusFilter}
                onChange={(e) => setExpStatusFilter(e.target.value)}
              >
                <option value="all">All statuses</option>
                <option value="trained">trained</option>
                <option value="failed">failed</option>
                <option value="deployed">deployed</option>
              </select>
              <button
                className="dash-btn success"
                onClick={deployBestFiltered}
                disabled={!bestFilteredByRmse || bestFilteredByRmse.is_deployed}
              >
                {bestFilteredByRmse?.is_deployed
                  ? "Best already deployed"
                  : "Deploy best filtered"}
              </button>
            </div>

            <div className="dash-table-wrap">
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Symbol</th>
                    <th>Model</th>
                    <th>Status</th>
                    <th>MAE</th>
                    <th>RMSE</th>
                    <th>MAPE</th>
                    <th>R²</th>
                    <th>Created</th>
                    <th>Deploy</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredExperiments.length === 0 ? (
                    <tr>
                      <td colSpan={10}>
                        <div className="dash-empty">
                          No experiments matched your filters.
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredExperiments.map((exp) => (
                      <tr key={exp.id}>
                        <td>{exp.id}</td>
                        <td>{exp.symbol}</td>
                        <td>{exp.model_name}</td>
                        <td>
                          <span
                            className={`dash-badge ${exp.is_deployed ? "green" : "blue"}`}
                          >
                            {exp.is_deployed ? "Deployed" : exp.status}
                          </span>
                        </td>
                        <td>{exp.metrics?.mae ?? "-"}</td>
                        <td>{exp.metrics?.rmse ?? "-"}</td>
                        <td>{exp.metrics?.mape ?? "-"}</td>
                        <td>{exp.metrics?.r2 ?? "-"}</td>
                        <td>{exp.created_at}</td>
                        <td>
                          <button
                            className="dash-btn primary"
                            disabled={exp.is_deployed}
                            onClick={() => deployExperiment(exp.id)}
                          >
                            {exp.is_deployed ? "Active" : "Deploy"}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="dash-card">
          <h3>Prediction vs Actual</h3>

          <div className="dash-grid-2">
            <div>
              <label>Symbol</label>
              <select
                value={pvSymbol}
                onChange={(e) => setPvSymbol(e.target.value)}
              >
                <option value="BTC-USD">BTC-USD</option>
                <option value="ETH-USD">ETH-USD</option>
                <option value="SOL-USD">SOL-USD</option>
              </select>
            </div>

            <div>
              <label>Model</label>
              <select
                value={pvModel}
                onChange={(e) => setPvModel(e.target.value)}
              >
                <option value="linear_regression">Linear Regression</option>
                <option value="random_forest">Random Forest</option>
                <option value="xgboost">XGBoost</option>
                <option value="svr">SVR</option>
                <option value="lstm">LSTM</option>
              </select>
            </div>
          </div>

          <button className="dash-btn primary" onClick={loadPredictionVsActual}>
            Load Comparison
          </button>

          {pvError && <div className="dash-alert error">{pvError}</div>}

          {pvActual && pvChartData && (
            <>
              <p className="dash-subtitle">
                MAE: {pvActual.metrics.mae.toFixed(2)} · RMSE:{" "}
                {pvActual.metrics.rmse.toFixed(2)}
              </p>
              <div style={{ height: 340 }}>
                <Line
                  data={pvChartData}
                  options={{ responsive: true, maintainAspectRatio: false }}
                />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
