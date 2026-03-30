import { create } from "zustand";

interface User {
  id: number;
  name: string;
  is_staff: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  role: "admin" | "tenant" | null;
}

interface AuthActions {
  setAuth: (user: User, accessToken: string, refreshToken: string) => Promise<void>;
  clearAuth: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  hydrateFromStorage: () => Promise<void>;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  role: null,

  setAuth: async (user, accessToken, refreshToken) => {
    const { setAccessToken, setRefreshToken } = await import("@/lib/secure-store");
    await setAccessToken(accessToken);
    await setRefreshToken(refreshToken);
    set({
      user,
      isAuthenticated: true,
      isLoading: false,
      role: user.is_staff ? "admin" : "tenant",
    });
  },

  clearAuth: async () => {
    const { clearTokens } = await import("@/lib/secure-store");
    await clearTokens();
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      role: null,
    });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  hydrateFromStorage: async () => {
    const { getAccessToken } = await import("@/lib/secure-store");
    const token = await getAccessToken();
    if (!token) {
      set({ isLoading: false });
      return;
    }
    try {
      const { apiClient } = await import("@/lib/api/client");
      const response = await apiClient.get<{
        id: number;
        first_name: string;
        last_name: string;
        is_staff: boolean;
      }>("/auth/me/");
      const data = response.data;
      const user: User = {
        id: data.id,
        name: `${data.first_name} ${data.last_name}`.trim(),
        is_staff: data.is_staff,
      };
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        role: user.is_staff ? "admin" : "tenant",
      });
    } catch {
      const { clearTokens } = await import("@/lib/secure-store");
      await clearTokens();
      set({ isLoading: false });
    }
  },
}));
