import { apiClient } from './client';
import type {
  CatalogFilmCard,
  FilmSortBy,
  GenreItem,
  PaginatedResponse,
} from './types';

export interface ListFilmsParams {
  lang?: 'ru' | 'en';
  genre?: string;
  country?: string;
  year_from?: number;
  year_to?: number;
  sort_by?: FilmSortBy;
  limit?: number;
  offset?: number;
}

export async function listFilms(
  params: ListFilmsParams = {},
): Promise<PaginatedResponse<CatalogFilmCard>> {
  const { data } = await apiClient.get<PaginatedResponse<CatalogFilmCard>>(
    '/api/films',
    { params },
  );
  return data;
}

export async function listGenres(lang: 'ru' | 'en' = 'ru'): Promise<GenreItem[]> {
  const { data } = await apiClient.get<GenreItem[]>('/api/genres', {
    params: { lang },
  });
  return data;
}

export async function listProductionCountries(
  lang: 'ru' | 'en' = 'ru',
): Promise<GenreItem[]> {
  const { data } = await apiClient.get<GenreItem[]>('/api/production-countries', {
    params: { lang },
  });
  return data;
}
