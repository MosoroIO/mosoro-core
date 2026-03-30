/* ------------------------------------------------------------------ */
/* React hook for authentication state                                 */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
import type { TokenRequest } from "../types/robot";

interface UseAuthReturn {
  isLoggedIn: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: TokenRequest) => Promise<void>;
  logout: () => void;
}

function useAuth(): UseAuthReturn {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(api.isAuthenticated());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoggedIn(api.isAuthenticated());
  }, []);

  const login = useCallback(async (credentials: TokenRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      await api.login(credentials);
      setIsLoggedIn(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    api.logout();
    setIsLoggedIn(false);
  }, []);

  return {
    isLoggedIn,
    isLoading,
    error,
    login,
    logout,
  };
}

export { useAuth };
