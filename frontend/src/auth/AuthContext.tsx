import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, apiErrorMessage, getToken, setToken, setUnauthorizedHandler } from "../api/client";
import type { components } from "../api/schema";
import { isEditorRole } from "./roles";

type UserOut = components["schemas"]["UserOut"];

interface AuthState {
  user: UserOut | null;
  /** True while we're still resolving an existing token on first load. */
  isLoading: boolean;
  isEditor: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

async function fetchMe(): Promise<UserOut> {
  const { data, error } = await api.GET("/api/auth/me");
  if (error) throw new Error(apiErrorMessage(error, "Не удалось получить профиль"));
  return data;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    if (!getToken()) {
      setIsLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // OAuth2PasswordRequestForm on the backend expects form-urlencoded
    // username/password — distinct enough from the rest of the JSON API that
    // it's simplest as a one-off fetch rather than forcing it through the
    // generated-schema client.
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(apiErrorMessage(body, "Неверный email или пароль"));
    }
    const data: components["schemas"]["Token"] = await res.json();
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const value: AuthState = {
    user,
    isLoading,
    isEditor: user ? isEditorRole(user.role) : false,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
