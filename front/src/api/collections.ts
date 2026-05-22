import { apiClient } from './client';
import type {
  CollectionDetail,
  CollectionSummary,
  PaginatedResponse,
} from './types';

export interface ListCollectionsParams {
  kind?: 'editorial' | 'custom' | 'auto';
  only_featured?: boolean;
  for_entity_id?: number;
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

export async function getCollection(collectionId: number): Promise<CollectionDetail> {
  const { data } = await apiClient.get<CollectionDetail>(
    `/api/collection/${collectionId}`,
  );
  return data;
}
