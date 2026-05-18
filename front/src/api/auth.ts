import { apiClient } from './client';
import type { AuthResponse, User } from './types';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData extends LoginCredentials {
  display_name: string;
  city?: string;
}

export async function login(creds: LoginCredentials): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/api/auth/login', creds);
  return data;
}

export async function register(reg: RegisterData): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/api/auth/register', reg);
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/api/auth/me');
  return data;
}
