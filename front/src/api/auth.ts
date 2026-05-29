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

export interface UpdateProfileData {
  display_name?: string;
  city?: string;
  preferred_language?: 'ru' | 'en';
}

export async function updateProfile(data: UpdateProfileData): Promise<User> {
  const { data: user } = await apiClient.put<User>('/api/auth/me', data);
  return user;
}

export async function uploadAvatar(file: File): Promise<User> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await apiClient.post<User>('/api/auth/me/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
