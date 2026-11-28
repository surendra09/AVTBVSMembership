import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setSessionExpiredHandler } from "@/services/api";
import type { Me } from "@/types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<Me>;
  register: (body: { full_name: string; email: string | null; phone: string; password: string }) => Promise<Me>;
  logout: () => Promise<void>;
  reload: () => Promise<Me | null>;
  setMe: (me: Me) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    // The readable CSRF cookie exists only while a session exists; skip the call for visitors.
    if (!document.cookie.split("; ").some((c) => c.startsWith("avtbvs_csrf="))) {
      setMe(null);
      return null;
    }
    try {
      const { data } = await api.get<Me>("/auth/me");
      setMe(data);
      return data;
    } catch {
      setMe(null);
      return null;
    }
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => setMe(null));
    reload().finally(() => setLoading(false));
  }, [reload]);

  const login = useCallback(async (identifier: string, password: string) => {
    const { data } = await api.post<Me>("/auth/login", { identifier, password });
    setMe({ user: data.user, membership: data.membership });
    return data;
  }, []);

  const register = useCallback(async (body: { full_name: string; email: string | null; phone: string; password: string }) => {
    const { data } = await api.post<Me>("/auth/register", body);
    setMe(data);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setMe(null);
    }
  }, []);

  const value = useMemo(() => ({ me, loading, login, register, logout, reload, setMe }),
    [me, loading, login, register, logout, reload]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export const isAdmin = (me: Me | null) => me?.user.role === "ADMIN" || me?.user.role === "SUPER_ADMIN";
export const homePathFor = (me: Me) =>
  me.user.role === "SUPER_ADMIN" ? "/super-admin" : me.user.role === "ADMIN" ? "/admin" : "/dashboard";
