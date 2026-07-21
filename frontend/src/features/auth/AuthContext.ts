import { createContext, useContext } from "react";

import type { User } from "../../types/api";

export type AuthContextValue = {
  user: User | undefined;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
};

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);

export function useAuth() {
  const value = useContext(AuthContext);

  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return value;
}