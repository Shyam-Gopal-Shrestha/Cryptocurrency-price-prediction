import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Register from "./pages/Register";
import Login from "./pages/Login";

function UserDashboard() {
  return <h1 style={{ padding: "40px" }}>User Dashboard</h1>;
}

function AdminDashboard() {
  return <h1 style={{ padding: "40px" }}>Admin Dashboard</h1>;
}

function ResearcherDashboard() {
  return <h1 style={{ padding: "40px" }}>Researcher Dashboard</h1>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/user-dashboard" element={<UserDashboard />} />
        <Route path="/admin-dashboard" element={<AdminDashboard />} />
        <Route path="/researcher-dashboard" element={<ResearcherDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}