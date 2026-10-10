import { create } from "zustand";
import { authApi } from "@/lib/auth";
import type { UserRead, RegisterRequest, LoginRequest } from "@/types/auth";

interface AuthState {
    // State 
    user: UserRead | null;
    isLoading: boolean;
    error: string | null;

    // Actions
    checkAuth: () => Promise<void>;
    login: (data: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => Promise<void>;
    clearAuth: () => void;
    clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    // Initial state
    user: null,
    isLoading: false,
    error: null,

    checkAuth: async () => {
        set({isLoading: true, error: null});
        try {
            const user = await authApi.me();
            set({user});
        } catch {
            set({ user: null });
        } finally {
            set({isLoading: false});
        }
    },
    login: async (data: LoginRequest) => {
        set({isLoading: true, error: null});
        try {
            const user = await authApi.login(data);
            set({user});
        } catch (error: unknown) {
            set({ user: null, error: error instanceof Error ? error.message : "Something went wrong"});
            throw error; // Propagate the error to the component
        } finally {
            set({isLoading: false});
        }
    },
    register: async (data: RegisterRequest) => {
        set({isLoading: true, error: null});
        try {
            const user = await authApi.register(data);
            set({user});
        } catch (error: unknown) {
            set({ user: null, error: error instanceof Error ? error.message : "Something went wrong"});
            throw error; // Propagate the error to the component
        } finally {
            set({isLoading: false});
        }
    },
    logout: async () => {
        set({isLoading: true, error: null});
        try {
            await authApi.logout();
            set({user: null});
        } catch (error: unknown) {
            set({ error: error instanceof Error ? error.message : "Something went wrong"});
            throw error; // Propagate the error to the component
        } finally {
            set({isLoading: false});
        }
    },
    clearAuth: () => {
        set({ user: null, error: null });
    },
    clearError: () => {
        set({error: null});
    }
}))
