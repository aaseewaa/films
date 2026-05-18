/**
 * Глобальный store авторизации.
 * Хранит JWT и данные пользователя.
 * Persistent: токен сохраняется в localStorage между сессиями.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/api/types';

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) =>
        set({ token, user, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      logout: () =>
        set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: 'filmcine-auth',
    }
  )
);
