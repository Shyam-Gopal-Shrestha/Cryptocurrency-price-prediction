import React, { useState } from "react";
import { loginUser } from "../services/authService";
import { useNavigate, Link } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const showFeedback = (text, type) => {
    setMessage(text);
    setMessageType(type);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");

    const { email, password } = formData;

    if (!email || !password) {
      return showFeedback("Please enter both email and password.", "error");
    }

    if (!/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(email)) {
      return showFeedback("Please enter a valid email address.", "error");
    }

    setLoading(true);

    try {
      const data = await loginUser({ email, password });
      showFeedback(data.message || "Login successful.", "success");

      setTimeout(() => {
        if (data.role === "admin") {
          navigate("/admin-dashboard");
        } else if (data.role === "researcher") {
          navigate("/researcher-dashboard");
        } else {
          navigate("/user-dashboard");
        }
      }, 1200);
    } catch (error) {
      showFeedback(error.message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Welcome Back</h1>
        <p style={styles.subtitle}>Sign in to continue.</p>

        <form onSubmit={handleSubmit}>
          <div style={styles.group}>
            <label>Email Address</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              style={styles.input}
            />
          </div>

          <div style={styles.group}>
            <label>Password</label>
            <div style={styles.passwordWrap}>
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={formData.password}
                onChange={handleChange}
                style={styles.input}
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                style={styles.eyeBtn}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {message && (
            <div
              style={{
                ...styles.feedback,
                backgroundColor:
                  messageType === "success" ? "#123524" : "#3b1c22",
                color: messageType === "success" ? "#bbf7d0" : "#fecaca",
              }}
            >
              {message}
            </div>
          )}

          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <p style={styles.linkText}>
          Do not have an account? <Link to="/register">Register here</Link>
        </p>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "linear-gradient(135deg, #0f172a, #111827, #1e293b)",
    padding: "20px",
  },
  card: {
    width: "100%",
    maxWidth: "500px",
    background: "#0f172acc",
    border: "1px solid #334155",
    borderRadius: "20px",
    padding: "32px",
    color: "white",
  },
  title: {
    marginBottom: "10px",
    fontSize: "2rem",
    textAlign: "center",
  },
  subtitle: {
    marginBottom: "24px",
    textAlign: "center",
    color: "#94a3b8",
  },
  group: {
    marginBottom: "16px",
  },
  input: {
    width: "100%",
    padding: "12px",
    borderRadius: "10px",
    border: "1px solid #475569",
    background: "#1e293b",
    color: "white",
    marginTop: "6px",
  },
  passwordWrap: {
    position: "relative",
  },
  eyeBtn: {
    position: "absolute",
    right: "10px",
    top: "50%",
    transform: "translateY(-50%)",
    border: "none",
    background: "transparent",
    color: "#38bdf8",
    cursor: "pointer",
  },
  feedback: {
    marginBottom: "16px",
    padding: "12px",
    borderRadius: "10px",
  },
  button: {
    width: "100%",
    padding: "14px",
    border: "none",
    borderRadius: "12px",
    background: "linear-gradient(135deg, #2563eb, #0891b2)",
    color: "white",
    fontWeight: "bold",
    cursor: "pointer",
  },
  linkText: {
    marginTop: "18px",
    textAlign: "center",
    color: "#94a3b8",
  },
};