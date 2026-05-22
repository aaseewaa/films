import { apiClient } from './client';
import type { ImageURLs } from './types';

export interface FavoriteItem {
  entity_id: number;
  entity_type: string;
  title: string;
  summary?: string | null;
  images: ImageURLs;
  release_year?: number | null;
  status: string;
  note?: string | null;
  added_at: string;
  watched_at?: string | null;
}

export interface FavoritesResponse {
  items: FavoriteItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface FavoriteCheckResponse {
  is_favorite: boolean;
  status: string | null;
}

export interface RatedFilmItem {
  entity_id: number;
  entity_type: string;
  title: string;
  images: ImageURLs;
  release_year?: number | null;
  rating: number;
  would_recommend?: boolean | null;
  rated_at: string;
  updated_at: string;
}

export interface MyRatingsResponse {
  items: RatedFilmItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface RatingBucket {
  rating: number;
  count: number;
}

export interface RatingDistribution {
  buckets: RatingBucket[];
  total: number;
  average: number | null;
}

export interface ProfileStats {
  ratings_count: number;
  favorites_count: number;
  watched_count: number;
  want_to_watch_count: number;
  views_count: number;
  searches_count: number;
}

export interface SearchHistoryItem {
  query_text: string;
  results_count: number;
  searched_at: string;
  language_code?: string | null;
}

export interface ViewHistoryItem {
  entity_id: number;
  entity_type: string;
  title: string;
  images: ImageURLs;
  viewed_at: string;
  duration_seconds?: number | null;
}

export interface HistoryResponse {
  searches: SearchHistoryItem[];
  views: ViewHistoryItem[];
}

export async function getFavorites(params?: {
  type?: 'film' | 'person';
  limit?: number;
  offset?: number;
}): Promise<FavoritesResponse> {
  const { data } = await apiClient.get<FavoritesResponse>('/api/favorites', {
    params,
  });
  return data;
}

export async function checkFavorite(entityId: number): Promise<FavoriteCheckResponse> {
  const { data } = await apiClient.get<FavoriteCheckResponse>(
    `/api/favorites/check/${entityId}`,
  );
  return data;
}

export async function addFavorite(entityId: number): Promise<void> {
  await apiClient.post(`/api/favorites/${entityId}`);
}

export async function removeFavorite(entityId: number): Promise<void> {
  await apiClient.delete(`/api/favorites/${entityId}`);
}

export async function getMyRatings(params?: {
  limit?: number;
  offset?: number;
}): Promise<MyRatingsResponse> {
  const { data } = await apiClient.get<MyRatingsResponse>('/api/ratings/me', {
    params,
  });
  return data;
}

export async function getRatingDistribution(): Promise<RatingDistribution> {
  const { data } = await apiClient.get<RatingDistribution>(
    '/api/ratings/me/distribution',
  );
  return data;
}

export async function getProfileStats(): Promise<ProfileStats> {
  const { data } = await apiClient.get<ProfileStats>('/api/profile/stats');
  return data;
}

export async function getHistory(limit = 50): Promise<HistoryResponse> {
  const { data } = await apiClient.get<HistoryResponse>('/api/history', {
    params: { limit },
  });
  return data;
}
