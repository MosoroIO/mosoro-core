/* ------------------------------------------------------------------ */
/* Authentication context provider                                     */
/* ------------------------------------------------------------------ */

import {
  createContext,
  useContext,
  type ReactNode,
} from "react";
import { useAuth } from "../hooks/use-auth";
import type { TokenRequest } from "../types/robot";

interface AuthContextValue {
  isLoggedIn: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: TokenRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

function AuthProvider({ children }: AuthProviderProps) {
  const auth = useAuth();

  return (
    <AuthContext.Provider value={auth}>
      {children}
    </AuthContext.Provider>
  );
}

function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
}

export { AuthProvider, useAuthContext };
