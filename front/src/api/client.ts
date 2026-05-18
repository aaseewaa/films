/**
 * Axios-клиент для запросов к бэку.
 * Vite proxy перенаправляет /api/* на http://localhost:8000
 * Авторизационный токен берётся из Zustand auth store.
 */
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

export const apiClient = axios.create({
  baseURL: '/',
  timeout: 30000,
});

// Интерцептор: добавляем JWT в каждый запрос если пользователь залогинен
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Интерцептор: обработка 401 — токен протух, выходим
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Не логаут на /api/auth/login — там 401 это «не тот пароль»
      const url = error.config?.url ?? '';
      if (!url.includes('/auth/login')) {
        useAuthStore.getState().logout();
      }
    }
    return Promise.reject(error);
  }
);
