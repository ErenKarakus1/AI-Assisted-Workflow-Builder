import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getCurrentUser } from "../../api/auth";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "../../api/client";
import type { TokenPair } from "../../types/api";
import { AuthContext, type AuthContextValue } from "./AuthContext";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const [hasToken, setHasToken] = useState(
    () => Boolean(getAccessToken()) || Boolean(getRefreshToken()),
  );

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
      signIn: async (tokens: TokenPair) => {
        setTokens(tokens);
        setHasToken(true);

        await queryClient.invalidateQueries({
          queryKey: ["current-user"],
        });
      },
      signOut: () => {
        clearTokens();
        setHasToken(false);
        queryClient.clear();
      },
    }),
    [hasToken, queryClient, userQuery.data, userQuery.isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}