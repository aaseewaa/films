import { apiClient } from './client';

export interface RatingItem {
  entity_id: number;
  rating: number;
  would_recommend: boolean | null;
  rated_at: string;
  updated_at: string;
}

export interface EntityRatingStats {
  avg_rating: number | null;
  total_ratings: number;
  recommend_percent: number | null;
}

export async function getMyRating(entityId: number): Promise<RatingItem | null> {
  const { data } = await apiClient.get<RatingItem | null>(
    `/api/ratings/me/${entityId}`,
  );
  return data;
}

export async function getEntityRatingStats(
  entityId: number,
): Promise<EntityRatingStats> {
  const { data } = await apiClient.get<EntityRatingStats>(
    `/api/ratings/stats/${entityId}`,
  );
  return data;
}

export async function setRating(
  entityId: number,
  rating: number,
): Promise<void> {
  await apiClient.put(`/api/ratings/${entityId}`, { rating });
}

export async function removeRating(entityId: number): Promise<void> {
  await apiClient.delete(`/api/ratings/${entityId}`);
}
