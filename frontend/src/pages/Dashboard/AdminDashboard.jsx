import React, { useContext, useEffect, useMemo, useState } from "react";
import api from "../../api/axios";
import { AuthContext } from "../../context/AuthContext";
import { LogOut } from "lucide-react";
import "./DashboardSuite.css";

const roles = ["user", "researcher", "admin"];

export default function AdminDashboard() {
  const { logout } = useContext(AuthContext);
  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pendingUsers, setPendingUsers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [cryptos, setCryptos] = useState([]);
  const [models, setModels] = useState([]);
  const [logs, setLogs] = useState([]);
  const [apiUsage, setApiUsage] = useState([]);
  const [newCrypto, setNewCrypto] = useState({
    symbol: "",
    name: "",
    is_enabled: true,
  });
  const [newModel, setNewModel] = useState({
    model_name: "",
    is_enabled: true,
    is_researcher_available: true,
  });

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [pending, users, cs, ms, ls, usage] = await Promise.all([
        api.get("/admin/pending-users"),
        api.get("/admin/users"),
        api.get("/admin/config/cryptos"),
        api.get("/admin/config/models"),
        api.get("/admin/logs"),
        api.get("/admin/api-usage"),
      ]);

      setPendingUsers(pending.data || []);
      setAllUsers(users.data || []);
      setCryptos(cs.data || []);
      setModels(ms.data || []);
      setLogs(ls.data || []);
      setApiUsage(usage.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load admin data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const approveUser = async (userId, approved) => {
    setError("");
    setMessage("");
    try {
      await api.post(`/admin/users/${userId}/approval`, { approved });
      setMessage(`User ${approved ? "approved" : "rejected"} successfully.`);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update user approval.");
    }
  };

  const updateRole = async (userId, role) => {
    setError("");
    setMessage("");
    try {
      await api.patch(`/admin/users/${userId}/role`, { role });
      setMessage("Role updated.");
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update role.");
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm("Delete this user account?")) return;
    setError("");
    setMessage("");
    try {
      await api.delete(`/admin/users/${userId}`);
      setMessage("User deleted.");
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete user.");
    }
  };

  const saveCrypto = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.post("/admin/config/cryptos", {
        ...newCrypto,
        symbol: newCrypto.symbol.trim(),
        name: newCrypto.name.trim(),
      });
      setMessage("Crypto configuration saved.");
      setNewCrypto({ symbol: "", name: "", is_enabled: true });
      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to save crypto configuration.",
      );
    }
  };

  const saveModel = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.post("/admin/config/models", {
        ...newModel,
        model_name: newModel.model_name.trim().toLowerCase(),
      });
      setMessage("Model configuration saved.");
      setNewModel({
        model_name: "",
        is_enabled: true,
        is_researcher_available: true,
      });
      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to save model configuration.",
      );
    }
  };

  const stats = useMemo(() => {
    const totalUsers = allUsers.length;
    const activeResearchers = allUsers.filter(
      (u) => u.role === "researcher" && u.status === "approved",
    ).length;
    const enabledCryptos = cryptos.filter((c) => c.is_enabled).length;
    const enabledModels = models.filter((m) => m.is_enabled).length;
    const apiCalls = apiUsage.reduce(
      (acc, item) => acc + (item.request_count || 0),
      0,
    );

    return {
      totalUsers,
      activeResearchers,
      enabledCryptos,
      enabledModels,
      apiCalls,
    };
  }, [allUsers, cryptos, models, apiUsage]);

  const menuItems = [
    { key: "dashboard", label: "Dashboard" },
    { key: "approvals", label: "User Approval" },
    { key: "users", label: "User Management" },
    { key: "crypto", label: "Crypto Configuration" },
    { key: "models", label: "Model Control" },
    { key: "logs", label: "Logs" },
    { key: "usage", label: "API Usage" },
  ];

  return (
    <div className="dash-layout">
      <aside className="dash-sidebar">
        <div>
          <div className="dash-brand">
            <span className="dash-brand-dot" />
            <h2>Admin Console</h2>
          </div>
          <p className="dash-subtitle">System control and governance</p>
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
            <h1>Admin Dashboard</h1>
            <p>
              Approve users, control model access, and monitor API/system
              activity.
            </p>
          </div>
          <span className="dash-chip">{loading ? "Syncing..." : "Live"}</span>
        </div>

        {error && <div className="dash-alert error">{error}</div>}
        {message && <div className="dash-alert success">{message}</div>}

        {(activeMenu === "dashboard" || activeMenu === "approvals") && (
          <div className="dash-grid-4" style={{ marginBottom: 12 }}>
            <div className="dash-card">
              <p className="dash-stat-label">Total users</p>
              <p className="dash-stat-value">{stats.totalUsers}</p>
            </div>
            <div className="dash-card">
              <p className="dash-stat-label">Active researchers</p>
              <p className="dash-stat-value">{stats.activeResearchers}</p>
            </div>
            <div className="dash-card">
              <p className="dash-stat-label">Enabled cryptocurrencies</p>
              <p className="dash-stat-value">{stats.enabledCryptos}</p>
            </div>
            <div className="dash-card">
              <p className="dash-stat-label">Tracked API calls</p>
              <p className="dash-stat-value">{stats.apiCalls}</p>
            </div>
          </div>
        )}

        {(activeMenu === "dashboard" || activeMenu === "approvals") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Pending registrations</h3>
            <div className="dash-table-wrap">
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingUsers.length === 0 ? (
                    <tr>
                      <td colSpan={6}>No pending users.</td>
                    </tr>
                  ) : (
                    pendingUsers.map((user) => (
                      <tr key={user.id}>
                        <td>{user.id}</td>
                        <td>{user.email}</td>
                        <td>{user.role}</td>
                        <td>
                          <span className="dash-badge yellow">
                            {user.status}
                          </span>
                        </td>
                        <td>{user.created_at}</td>
                        <td>
                          <div className="dash-actions">
                            <button
                              className="dash-btn success"
                              onClick={() => approveUser(user.id, true)}
                            >
                              Approve
                            </button>
                            <button
                              className="dash-btn danger"
                              onClick={() => approveUser(user.id, false)}
                            >
                              Reject
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "users") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>User management</h3>
            <div className="dash-table-wrap">
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Role control</th>
                    <th>Delete</th>
                  </tr>
                </thead>
                <tbody>
                  {allUsers.map((u) => (
                    <tr key={u.id}>
                      <td>{u.id}</td>
                      <td>{u.email}</td>
                      <td>{u.role}</td>
                      <td>
                        <span
                          className={`dash-badge ${u.status === "approved" ? "green" : u.status === "pending" ? "yellow" : "red"}`}
                        >
                          {u.status}
                        </span>
                      </td>
                      <td>{u.created_at}</td>
                      <td>
                        <select
                          className="dash-select"
                          value={u.role}
                          onChange={(e) => updateRole(u.id, e.target.value)}
                        >
                          {roles.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <button
                          className="dash-btn danger"
                          onClick={() => deleteUser(u.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "crypto") && (
          <section className="dash-grid-2" style={{ marginBottom: 12 }}>
            <div className="dash-card">
              <h3>Crypto configuration</h3>
              <form onSubmit={saveCrypto}>
                <div className="dash-form-grid">
                  <div className="dash-form-row">
                    <label>Symbol</label>
                    <input
                      className="dash-input"
                      value={newCrypto.symbol}
                      onChange={(e) =>
                        setNewCrypto((p) => ({
                          ...p,
                          symbol: e.target.value.toUpperCase(),
                        }))
                      }
                      placeholder="BTC-USD"
                      required
                    />
                  </div>
                  <div className="dash-form-row">
                    <label>Name</label>
                    <input
                      className="dash-input"
                      value={newCrypto.name}
                      onChange={(e) =>
                        setNewCrypto((p) => ({ ...p, name: e.target.value }))
                      }
                      placeholder="Bitcoin"
                      required
                    />
                  </div>
                </div>
                <label className="dash-switch" style={{ margin: "10px 0" }}>
                  <input
                    type="checkbox"
                    checked={newCrypto.is_enabled}
                    onChange={(e) =>
                      setNewCrypto((p) => ({
                        ...p,
                        is_enabled: e.target.checked,
                      }))
                    }
                  />
                  Enabled
                </label>
                <button className="dash-btn primary" type="submit">
                  Save cryptocurrency
                </button>
              </form>
            </div>

            <div className="dash-card">
              <h3>Configured cryptocurrencies</h3>
              <div className="dash-table-wrap">
                <table className="dash-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Name</th>
                      <th>Enabled</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cryptos.map((c) => (
                      <tr key={c.id || c.symbol}>
                        <td>{c.symbol}</td>
                        <td>{c.name}</td>
                        <td>
                          <span
                            className={`dash-badge ${c.is_enabled ? "green" : "red"}`}
                          >
                            {c.is_enabled ? "Enabled" : "Disabled"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "models") && (
          <section className="dash-grid-2" style={{ marginBottom: 12 }}>
            <div className="dash-card">
              <h3>Model control</h3>
              <form onSubmit={saveModel}>
                <div className="dash-form-row">
                  <label>Model name</label>
                  <input
                    className="dash-input"
                    value={newModel.model_name}
                    onChange={(e) =>
                      setNewModel((p) => ({ ...p, model_name: e.target.value }))
                    }
                    placeholder="xgboost"
                    required
                  />
                </div>
                <label className="dash-switch" style={{ margin: "10px 0" }}>
                  <input
                    type="checkbox"
                    checked={newModel.is_enabled}
                    onChange={(e) =>
                      setNewModel((p) => ({
                        ...p,
                        is_enabled: e.target.checked,
                      }))
                    }
                  />
                  Enabled globally
                </label>
                <label className="dash-switch" style={{ marginBottom: 12 }}>
                  <input
                    type="checkbox"
                    checked={newModel.is_researcher_available}
                    onChange={(e) =>
                      setNewModel((p) => ({
                        ...p,
                        is_researcher_available: e.target.checked,
                      }))
                    }
                  />
                  Available to researchers
                </label>
                <button className="dash-btn primary" type="submit">
                  Save model policy
                </button>
              </form>
            </div>

            <div className="dash-card">
              <h3>Available models</h3>
              <div className="dash-table-wrap">
                <table className="dash-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Enabled</th>
                      <th>Researcher access</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.map((m) => (
                      <tr key={m.id || m.model_name}>
                        <td>{m.model_name}</td>
                        <td>
                          <span
                            className={`dash-badge ${m.is_enabled ? "green" : "red"}`}
                          >
                            {m.is_enabled ? "Yes" : "No"}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`dash-badge ${m.is_researcher_available ? "blue" : "red"}`}
                          >
                            {m.is_researcher_available ? "Allowed" : "Blocked"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "logs") && (
          <section className="dash-card" style={{ marginBottom: 12 }}>
            <h3>Activity logs</h3>
            <div className="dash-table-wrap">
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice(0, 50).map((log) => (
                    <tr key={log.id}>
                      <td>{log.created_at}</td>
                      <td>{log.email || `user:${log.user_id}`}</td>
                      <td>{log.action}</td>
                      <td>{log.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {(activeMenu === "dashboard" || activeMenu === "usage") && (
          <section className="dash-card">
            <h3>API usage monitoring</h3>
            <div className="dash-table-wrap">
              <table className="dash-table">
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Endpoint</th>
                    <th>Requests</th>
                    <th>Last called</th>
                    <th>User ID</th>
                  </tr>
                </thead>
                <tbody>
                  {apiUsage.map((item, idx) => (
                    <tr key={`${item.provider}-${item.endpoint}-${idx}`}>
                      <td>{item.provider}</td>
                      <td>{item.endpoint}</td>
                      <td>{item.request_count}</td>
                      <td>{item.last_called_at || "-"}</td>
                      <td>{item.user_id ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
