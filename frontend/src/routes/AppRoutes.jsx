import { Routes, Route } from "react-router-dom";
import Login from "../pages/Auth/Login";
import Signup from "../pages/Auth/Signup";
import Home from "../pages/Dashboard/Home";
import AdminDashboard from "../pages/Dashboard/AdminDashboard";
import ResearcherDashboard from "../pages/Dashboard/ResearcherWorkbench";
import UserDashboard from "../pages/Dashboard/UserDashboard";
import ProtectedRoute from "../components/ProtectedRoutes";

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
