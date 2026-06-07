import { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../../../context/AuthContext";

export default function ProtectedRoute({ children, role, roles }) {
  const { isAuthenticated, user, initializing } = useContext(AuthContext);

  if (initializing) {
    return <div style={{ padding: 24 }}>Loading session...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role && user?.role !== role) {
    return <Navigate to="/login" replace />;
  }

  if (roles?.length && !roles.includes(user?.role)) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
