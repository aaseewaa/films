import { apiClient } from './client';
import type { EntityDetail, FilmDetail } from './types';

export async function getEntity(entityId: number): Promise<EntityDetail> {
  const { data } = await apiClient.get<EntityDetail>(`/api/entity/${entityId}`);
  return data;
}

export async function getFilm(entityId: number): Promise<FilmDetail> {
  const { data } = await apiClient.get<FilmDetail>(`/api/entity/${entityId}`);
  return data;
}
