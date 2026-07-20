import { createContext, useContext, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getCurrentUser } from "../../api/auth";
import { clearAccessToken, getAccessToken, setAccessToken } from "../../api/client";
import type { User } from "../../types/api";

type AuthContextValue = {
  user: User | undefined;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(() => Boolean(getAccessToken()));

  const userQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: getCurrentUser,
    enabled: hasToken,
    retry: false,
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user: userQuery.data,
      isAuthenticated: Boolean(userQuery.data && hasToken),
      isLoading: hasToken && userQuery.isLoading,
      signIn: async (token: string) => {
        setAccessToken(token);
        setHasToken(true);
        await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      },
      signOut: () => {
        clearAccessToken();
        setHasToken(false);
        queryClient.clear();
      },
    }),
    [hasToken, queryClient, userQuery.data, userQuery.isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

