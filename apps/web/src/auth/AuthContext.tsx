import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setUnauthorizedHandler, type User } from "../api/client";

type Ctx = {
  user: User | null;
  loading: boolean;
  login: (e: string, p: string) => Promise<void>;
  signup: (e: string, p: string) => Promise<void>;
  logout: () => Promise<void>;
};
const AuthCtx = createContext<Ctx>(null!);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));   // expired session -> back to the login page
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (e: string, p: string) => setUser(await api.login(e, p)), []);
  const signup = useCallback(async (e: string, p: string) => setUser(await api.signup(e, p)), []);
  const logout = useCallback(async () => { await api.logout(); setUser(null); }, []);

  return <AuthCtx.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthCtx.Provider>;
}
