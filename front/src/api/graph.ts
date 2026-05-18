import { apiClient } from './client';

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

export interface RadialPerson {
  id: number;
  name: string;
  image: string | null;
  weight: number;
  films_count: number;
}

export interface RadialRing1Node extends RadialPerson {
  ring2: RadialPerson[];
}

export interface RadialCenter {
  id: number;
  name: string;
  image: string | null;
}

export interface RadialResponse {
  center: RadialCenter;
  ring1: RadialRing1Node[];
  neighbors: RadialPerson[];
  ring1_count: number;
  ring2_per_node: number;
  top_n_requested: number;
}

export async function getRadialGraph(
  directorId: number,
  topN = 4,
  ring2N = 3,
  lang: 'ru' | 'en' = 'ru'
): Promise<RadialResponse> {
  const { data } = await apiClient.get<RadialResponse>(
    `/api/graph/director/${directorId}/radial`,
    {
      params: { top_n: topN, ring2_n: ring2N, lang },
    }
  );
  return data;
}

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
