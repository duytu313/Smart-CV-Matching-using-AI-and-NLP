"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { auth, User, setAuthToken, getAuthToken } from "./api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    role: "candidate" | "recruiter";
    company_name?: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Check for existing token on mount
    const token = getAuthToken();
    if (token) {
      auth
        .me()
        .then(setUser)
        .catch(() => {
          setAuthToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await auth.login(email, password);
    setAuthToken(response.access_token);
    setUser(response.user);

    // Redirect based on role
    if (response.user.role === "recruiter") {
      router.push("/recruiter/dashboard");
    } else {
      router.push("/candidate/dashboard");
    }
  };

  const register = async (data: {
    email: string;
    password: string;
    full_name: string;
    role: "candidate" | "recruiter";
    company_name?: string;
  }) => {
    const response = await auth.register(data);
    setAuthToken(response.access_token);
    setUser(response.user);

    // Redirect based on role after registration
    if (response.user.role === "recruiter") {
      router.push("/recruiter/dashboard");
    } else {
      router.push("/candidate/dashboard");
    }
  };

  const logout = () => {
    // Clear auth data
    setAuthToken(null);
    setUser(null);

    // Redirect to login page - QUAN TRỌNG: sửa đường dẫn đúng
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
