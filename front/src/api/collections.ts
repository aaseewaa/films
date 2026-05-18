import { apiClient } from './client';
import type {
  CollectionDetail,
  CollectionSummary,
  PaginatedResponse,
} from './types';

export interface ListCollectionsParams {
  kind?: 'editorial' | 'custom' | 'auto';
  only_featured?: boolean;
  lang?: 'ru' | 'en';
  limit?: number;
  offset?: number;
}

export async function listCollections(
  params: ListCollectionsParams = {}
): Promise<PaginatedResponse<CollectionSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<CollectionSummary>>(
    '/api/collections',
    { params }
  );
  return data;
}

export async function getCollection(
  collectionId: number,
  lang: 'ru' | 'en' = 'ru'
): Promise<CollectionDetail> {
  const { data } = await apiClient.get<CollectionDetail>(
    `/api/collection/${collectionId}`,
    { params: { lang } }
  );
  return data;
}
