"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { apiClient, UserProfile } from "@/services/apiClient";

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<any>;
  verifyOTP: (userId: string, otpCode: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const initAuth = async () => {
    setIsLoading(true);
    try {
      if (typeof window !== "undefined") {
        // The session itself is an httpOnly cookie; the stored profile only says one may exist.
        // Tokens kept in localStorage by older versions are discarded.
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (localStorage.getItem("user_profile")) {
          const profile = await apiClient.getMe();
          setUser(profile);
          localStorage.setItem("user_profile", JSON.stringify(profile));
        }
      }
    } catch {
      apiClient.clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<any> => {
    setIsLoading(true);
    try {
      const response = await apiClient.login(email, password);
      if (response.requires_2fa) {
        return response;
      }
      setUser(response.user);
      return response;
    } finally {
      setIsLoading(false);
    }
  };

  const verifyOTP = async (userId: string, otpCode: string): Promise<UserProfile> => {
    setIsLoading(true);
    try {
      const response = await apiClient.verifyOTP(userId, otpCode);
      setUser(response.user);
      return response.user;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    await apiClient.logout();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/auth/login";
    }
  };

  const refreshUser = async () => {
    try {
      const profile = await apiClient.getMe();
      setUser(profile);
    } catch {
      await logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        verifyOTP,
        logout,
        refreshUser,
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
