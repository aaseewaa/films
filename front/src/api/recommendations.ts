import { apiClient } from './client';
import type { RecommendationMode, RecommendationsResponse } from './types';

export interface RecommendationsParams {
  for_film_id?: number;
  for_person_id?: number;
  mode?: RecommendationMode;
  lang?: 'ru' | 'en';
  limit?: number;
}

export async function getRecommendations(
  params: RecommendationsParams
): Promise<RecommendationsResponse> {
  const { data } = await apiClient.get<RecommendationsResponse>('/api/recommendations', {
    params,
  });
  return data;
}
