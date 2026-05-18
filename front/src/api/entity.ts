import { apiClient } from './client';
import type { EntityDetail, FilmDetail } from './types';

export async function getEntity(
  entityId: number,
  lang: 'ru' | 'en' = 'ru'
): Promise<EntityDetail> {
  const { data } = await apiClient.get<EntityDetail>(`/api/entity/${entityId}`, {
    params: { lang },
  });
  return data;
}

export async function getFilm(entityId: number, lang: 'ru' | 'en' = 'ru'): Promise<FilmDetail> {
  const { data } = await apiClient.get<FilmDetail>(`/api/entity/${entityId}`, {
    params: { lang },
  });
  return data;
}
