import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { api, ApiError, can } from "../api/client";
import type { SessionUser } from "../api/types";

interface AuthState {
  user: SessionUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<SessionUser>;
  logout: () => Promise<void>;
  allowed: (permission: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const session = await api.session();
      if (session.authenticated && session.user) return session.user;
      if (session.refresh_available) {
        try {
          return await api.refresh();
        } catch (err) {
          if (err instanceof ApiError && err.status === 401) return null;
          throw err;
        }
      }
      return null;
    },
    retry: false,
  });

  const value: AuthState = {
    user: me.data ?? null,
    loading: me.isLoading,
    allowed: (permission) => can(me.data ?? null, permission),
    login: async (email, password) => {
      const user = await api.login(email, password);
      queryClient.setQueryData(["auth", "me"], user);
      return user;
    },
    logout: async () => {
      try {
        await api.logout();
      } finally {
        queryClient.setQueryData(["auth", "me"], null);
        queryClient.clear();
      }
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
