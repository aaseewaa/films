import { apiClient } from './client';

// ────────────────────────────────────────────────
// Старые типы (для совместимости с остальным кодом)
// ────────────────────────────────────────────────
export interface GraphNode {
  id: number;
  name: string;
  image?: string | null;
  group?: string;
  influences_count?: number;
  influenced_by_count?: number;
  is_center?: boolean;
}

export interface GraphLink {
  source: number;
  target: number;
  weight?: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  links: GraphLink[];
  center_id?: number | null;
  depth?: number;
}

// ────────────────────────────────────────────────
// НОВЫЙ радиальный endpoint
// ────────────────────────────────────────────────

export interface RadialNeighbor {
  id: number;
  name: string;
  image: string | null;
  weight: number;
  films_count: number;
}

export interface RadialCenter {
  id: number;
  name: string;
  image: string | null;
}

export interface RadialResponse {
  center: RadialCenter;
  neighbors: RadialNeighbor[];
  total_neighbors_in_db: number;
  top_n_requested: number;
}

/**
 * Центр + топ-N значимых соседей по силе связи.
 * Глубина строго 1 — для радиальной карточки на главной.
 */
export async function getRadialGraph(
  directorId: number,
  topN = 4,
  lang: 'ru' | 'en' = 'ru'
): Promise<RadialResponse> {
  const { data } = await apiClient.get<RadialResponse>(
    `/api/graph/director/${directorId}/radial`,
    {
      params: { top_n: topN, lang },
    }
  );
  return data;
}

// ────────────────────────────────────────────────
// Старые методы (оставляем для совместимости)
// ────────────────────────────────────────────────

export async function getFullGraph(limit = 50): Promise<GraphResponse> {
  const { data } = await apiClient.get<GraphResponse>('/api/graph/full', {
    params: { limit },
  });
  return data;
}

export async function getDirectorGraph(
  directorId: number,
  depth = 2,
  maxNodes = 80
): Promise<GraphResponse> {
  const { data } = await apiClient.get<GraphResponse>(
    `/api/graph/director/${directorId}`,
    {
      params: { depth, lang: 'ru', max_nodes: maxNodes },
    }
  );
  return data;
}
