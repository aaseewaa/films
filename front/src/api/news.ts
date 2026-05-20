import { apiClient } from './client';
import type { ImageURLs } from './types';

export interface NewsCity {
  name: string;
  slug: string;
  kp_city_id: string;
}

export interface NewsFilmItem {
  kinopoisk_id: number | null;
  title: string;
  entity_id: number | null;
  release_year: number | null;
  summary: string | null;
  images: ImageURLs;
  ticket_url: string;
  ticket_provider: 'kinopoisk';
  cinemas: string[];
  in_database: boolean;
  tmdb_id: number | null;
}

export interface NewsResponse {
  city: string;
  city_kp_id: string;
  source: string;
  fetched_at: string;
  items: NewsFilmItem[];
  total: number;
  limit: number;
}

export interface ListNewsParams {
  scope?: 'city' | 'world';
  city?: string;
  lang?: 'ru' | 'en';
  limit?: number;
}

export async function listNews(params: ListNewsParams = {}): Promise<NewsResponse> {
  const { data } = await apiClient.get<NewsResponse>('/api/news', { params });
  return data;
}

export async function listUpcoming(limit = 8): Promise<NewsResponse> {
  const { data } = await apiClient.get<NewsResponse>('/api/news/upcoming', {
    params: { limit },
  });
  return data;
}

export async function getFilmAfisha(
  entityId: number,
  city?: string,
): Promise<NewsFilmItem> {
  const { data } = await apiClient.get<NewsFilmItem>(`/api/news/film/${entityId}`, {
    params: city ? { city } : undefined,
  });
  return data;
}

export async function listNewsCities(): Promise<NewsCity[]> {
  const { data } = await apiClient.get<NewsCity[]>('/api/news/cities');
  return data;
}
