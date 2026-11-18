import { t } from "../i18n";
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

// Set when someone presses "Выйти" so the demo auto-login steps aside and the
// login page stays up (e.g. to sign in as another role). Per-tab on purpose:
// the next visit opens straight into the app again.
const LOGGED_OUT_KEY = "retail_logged_out";

function loggedOutOnPurpose(): boolean {
  try {
    return sessionStorage.getItem(LOGGED_OUT_KEY) === "1";
  } catch {
    return false;
  }
}

function setLoggedOutOnPurpose(on: boolean): void {
  try {
    if (on) sessionStorage.setItem(LOGGED_OUT_KEY, "1");
    else sessionStorage.removeItem(LOGGED_OUT_KEY);
  } catch {
    /* storage blocked — auto-login just stays on */
  }
}

/** Passwordless sign-in as the demo user; null when the backend has it off. */
async function demoLogin(): Promise<components["schemas"]["Token"] | null> {
  try {
    const res = await fetch("/api/auth/demo", { method: "POST" });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

async function fetchMe(): Promise<UserOut> {
  const { data, error } = await api.GET("/api/auth/me");
  if (error) throw new Error(apiErrorMessage(error, t("Не удалось получить профиль")));
  return data;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    setLoggedOutOnPurpose(true);
    setToken(null);
    setUser(null);
  }, []);

  /** Signs in as the demo user unless the visitor logged out on purpose. */
  const tryDemoLogin = useCallback(async () => {
    if (loggedOutOnPurpose()) return;
    const data = await demoLogin();
    if (!data) return;
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  useEffect(() => {
    // A 401 means the token expired: drop it and, on the demo, quietly sign
    // back in rather than bouncing the visitor to the login page.
    setUnauthorizedHandler(() => {
      setToken(null);
      setUser(null);
      setIsLoading(true);
      tryDemoLogin().finally(() => setIsLoading(false));
    });
  }, [tryDemoLogin]);

  useEffect(() => {
    const restore = getToken()
      ? fetchMe()
          .then(setUser)
          .catch(() => {
            setToken(null);
            return tryDemoLogin();
          })
      : tryDemoLogin();
    restore.finally(() => setIsLoading(false));
  }, [tryDemoLogin]);

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
      throw new Error(apiErrorMessage(body, t("Неверный email или пароль")));
    }
    const data: components["schemas"]["Token"] = await res.json();
    setLoggedOutOnPurpose(false);
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
