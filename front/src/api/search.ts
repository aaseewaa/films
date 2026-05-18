import { apiClient } from './client';
import type { SearchMode, SearchResponse } from './types';

export interface SearchParams {
  q: string;
  mode?: SearchMode;
  lang?: 'ru' | 'en';
  type?: 'film' | 'person';
  genre?: string;
  year_from?: number;
  year_to?: number;
  limit?: number;
  offset?: number;
}

export async function searchEntities(params: SearchParams): Promise<SearchResponse> {
  const { data } = await apiClient.get<SearchResponse>('/api/search', { params });
  return data;
}
