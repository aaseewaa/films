import { apiClient } from './client';
import type {
  CatalogFilmCard,
  FilmSortBy,
  GenreItem,
  PaginatedResponse,
} from './types';

export type FilmCatalogType = 'films' | 'animation';

export interface ListFilmsParams {
  lang?: 'ru' | 'en';
  catalog?: FilmCatalogType;
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

export async function listGenres(): Promise<GenreItem[]> {
  const { data } = await apiClient.get<GenreItem[]>('/api/genres');
  return data;
}

export async function listProductionCountries(): Promise<GenreItem[]> {
  const { data } = await apiClient.get<GenreItem[]>('/api/production-countries');
  return data;
}
