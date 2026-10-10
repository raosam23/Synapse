export interface UserRead {
    id: number;
    email: string;
    name: string | null;
    created_at: string;
};

export interface RegisterRequest {
    email: string;
    password: string;
    name?: string;
};

export interface LoginRequest {
    email: string;
    password: string;
};