import { useState } from "react";
import axios from "axios";

export default function Signup() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    role: "user",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.email.trim() || !form.password.trim()) {
      setError("Email and password are required.");
      return;
    }

    if (form.password.trim().length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    try {
      await axios.post("http://127.0.0.1:8000/signup", form);
      setSuccess("User created successfully. You can now login.");
      setForm({ email: "", password: "", role: "user" });
    } catch (err) {
      setError(err.response?.data?.detail || "Signup failed. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        placeholder="Email"
        type="email"
        value={form.email}
        required
        onChange={(e) => setForm({ ...form, email: e.target.value })}
      />
      <input
        type="password"
        placeholder="Password"
        value={form.password}
        minLength={6}
        required
        onChange={(e) => setForm({ ...form, password: e.target.value })}
      />

      <select
        value={form.role}
        onChange={(e) => setForm({ ...form, role: e.target.value })}
      >
        <option value="user">User</option>
        <option value="researcher">Researcher</option>
      </select>

      <button>Signup</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {success && <p style={{ color: "green" }}>{success}</p>}
    </form>
  );
}
