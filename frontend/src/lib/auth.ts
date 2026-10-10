import { api } from "./api";
import { RegisterRequest, LoginRequest, UserRead } from "../types/auth";

export const authApi = {
    register: (data: RegisterRequest) => api.post<UserRead>("/api/v1/auth/register", data),
    login: (data: LoginRequest) => api.post<UserRead>("/api/v1/auth/login", data),
    logout: () => api.post<{message: string}>("/api/v1/auth/logout", {}),
    me: () => api.get<UserRead>("/api/v1/auth/me"),
};