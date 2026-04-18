import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import api from "../api/axios";

export const AuthContext = createContext(null);

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || "");
  const [initializing, setInitializing] = useState(true);

  const persistSession = useCallback((nextToken, nextUser) => {
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken("");
    setUser(null);
  }, []);

  useEffect(() => {
    let mounted = true;

    const boot = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      const storedUserRaw = localStorage.getItem(USER_KEY);

      if (!storedToken) {
        if (mounted) setInitializing(false);
        return;
      }

      try {
        const me = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${storedToken}` },
        });
        if (!mounted) return;
        setToken(storedToken);
        setUser(me.data || (storedUserRaw ? JSON.parse(storedUserRaw) : null));
      } catch {
        if (!mounted) return;
        clearSession();
      } finally {
        if (mounted) setInitializing(false);
      }
    };

    boot();
    return () => {
      mounted = false;
    };
  }, [clearSession]);

  const login = async ({ email, password, otp_code }) => {
    const res = await api.post("/login", { email, password, otp_code });
    if (res.data?.requires_2fa) return res.data;

    const nextUser = {
      id: res.data.id,
      email: res.data.email,
      role: res.data.role,
      status: res.data.status,
    };
    persistSession(res.data.token, nextUser);
    return res.data;
  };

  const logout = async () => {
    try {
      if (token) {
        await api.post("/logout", null, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } catch {
      // ignore network/logout race
    } finally {
      clearSession();
    }
  };

  const value = useMemo(
    () => ({
      user,
      token,
      initializing,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      setUser,
    }),
    [user, token, initializing, persistSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
