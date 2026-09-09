/**
 * Auth state.
 *
 * The token is held in `src/lib/api.ts`, in a module variable backed by
 * `sessionStorage` — see the comment there for why that and not `localStorage`,
 * and why not memory only. This file's job is the other half: on a fresh page
 * load, a stored token is only a claim, so it is exchanged for the user via
 * `/auth/me` before any screen renders. A token the server no longer accepts is
 * discarded and the login screen shown, which is what an expired one looks like
 * after an hour.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  type CurrentUser,
  getToken,
  login as apiLogin,
  me as apiMe,
  setToken,
} from "@/lib/api";

interface AuthValue {
  user: CurrentUser | null;
  /** True only while a stored token is being exchanged for a user on load.
   *  Screens must not render and the login screen must not flash until it is
   *  false, or a refresh bounces the officer to a sign-in they do not need. */
  restoring: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  // Read once, at mount: if there is no token there is nothing to restore and
  // the login screen should appear immediately, with no flicker through a
  // loading state.
  const [restoring, setRestoring] = useState<boolean>(() => getToken() !== null);

  useEffect(() => {
    if (!restoring) return;
    let live = true;
    apiMe()
      .then((u) => {
        if (live) setUser(u);
      })
      .catch(() => {
        // Expired, revoked, or the API is down. Either way this token cannot be
        // used, so drop it rather than leave a dead credential in storage.
        if (live) setToken(null);
      })
      .finally(() => {
        if (live) setRestoring(false);
      });
    return () => {
      live = false;
    };
    // Mount only. `restoring` is the initial read and never goes back to true.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, restoring, signIn, signOut }),
    [user, restoring, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth used outside AuthProvider");
  return ctx;
}
