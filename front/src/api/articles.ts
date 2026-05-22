import { apiClient } from './client';
import type {
  ArticleDetail,
  ArticleSummary,
  PaginatedResponse,
} from './types';

export interface ListArticlesParams {
  only_featured?: boolean;
  article_type?: string;
  for_entity_id?: number;
  lang?: 'ru' | 'en';
  limit?: number;
  offset?: number;
}

export async function listArticles(
  params: ListArticlesParams = {}
): Promise<PaginatedResponse<ArticleSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<ArticleSummary>>(
    '/api/articles',
    { params }
  );
  return data;
}

export async function getArticleBySlug(slug: string): Promise<ArticleDetail> {
  const { data } = await apiClient.get<ArticleDetail>(`/api/article/${slug}`);
  return data;
}
