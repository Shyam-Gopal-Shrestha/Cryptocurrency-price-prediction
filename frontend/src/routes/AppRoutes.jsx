import { Routes, Route } from "react-router-dom";
import Login from "../pages/Auth/Login";
import Signup from "../pages/Auth/Signup";
import Home from "../pages/Dashboard/Home";
import AdminDashboard from "../pages/Dashboard/AdminDashboard";
import ResearcherDashboard from "../pages/Dashboard/ResearcherWorkbench";
import UserDashboard from "../pages/Dashboard/UserDashboard";
import { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";

function ProtectedRoute({ children, roles, role }) {
  const { isAuthenticated, user, initializing } = useContext(AuthContext);

  if (initializing)
    return <div style={{ padding: 24 }}>Loading session...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (role && user?.role !== role) return <Navigate to="/login" replace />;
  if (roles?.length && !roles.includes(user?.role))
    return <Navigate to="/login" replace />;

  return children;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/" element={<Home />} />
      <Route
        path="/admin"
        element={
          <ProtectedRoute role="admin">
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/researcher"
        element={
          <ProtectedRoute role="researcher">
            <ResearcherDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/user"
        element={
          <ProtectedRoute role="user">
            <UserDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Login />} />
    </Routes>
  );
}
