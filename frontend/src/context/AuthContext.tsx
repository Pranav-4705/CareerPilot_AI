"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { UserProfile, getMeApi } from "@/lib/api";

const TOKEN_STORAGE_KEY = "careerpilot_token";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      // Handle private browsing or localStorage disabled
    }
    setToken(null);
    setUser(null);
  }, []);

  const loadUserProfile = useCallback(async (authToken: string) => {
    try {
      const profile = await getMeApi(authToken);
      setUser(profile);
      setToken(authToken);
    } catch {
      // If token is invalid or expired, clean up
      logout();
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    try {
      const savedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (savedToken) {
        setToken(savedToken);
        loadUserProfile(savedToken);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  }, [loadUserProfile]);

  const login = async (newToken: string) => {
    setLoading(true);
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
      setToken(newToken);
      await loadUserProfile(newToken);
    } catch (err) {
      setLoading(false);
      throw err;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
