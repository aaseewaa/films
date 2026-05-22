/**
 * TypeScript-типы, отражающие Pydantic-схемы бэка.
 * Когда обновляется бэк — обновляются и эти типы.
 */

export type EntityType = 'film' | 'person' | 'article' | 'collection';

export interface ImageURLs {
  primary?: string | null;
  thumbnail?: string | null;
}

// ─── Поиск ───────────────────────────────────────
export type SearchMode = 'hybrid' | 'semantic';

export interface SearchHit {
  entity_id: number;
  entity_type: EntityType;
  title: string;
  summary?: string | null;
  images: ImageURLs;
  language_code?: string | null;
  release_year?: number | null;
  is_director?: boolean | null;
  is_actor?: boolean | null;
  score: number;
  match_type: 'fulltext' | 'fuzzy' | 'exact' | 'semantic';
}

export interface SearchResponse {
  query: string;
  detected_language: string;
  items: SearchHit[];
  total: number;
  limit: number;
  offset: number;
  mode: SearchMode;
  used_strategies: string[];
}

// ─── Граф ────────────────────────────────────────
export interface GraphNode {
  id: number;
  name: string;
  image?: string | null;
  group?: string;                  // "director"
  influences_count?: number;       // на кого ОН повлиял
  influenced_by_count?: number;    // КТО повлиял на него
  is_center?: boolean;             // флаг центра графа
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

// ─── Фильмы / Персоны ────────────────────────────
export interface FilmShort {
  entity_id: number;
  entity_type: 'film';
  title: string;
  release_year?: number | null;
  images: ImageURLs;
  summary?: string | null;
}

/** Карточка фильма в фильмографии персоны (ответ /api/entity/{id}). */
export interface PersonFilmographyItem {
  id: number;
  title: string;
  original_title?: string | null;
  release_year?: number | null;
  images: ImageURLs;
  role_type?: string | null;
  media_kind?: string | null;
  genres?: string[];
  country?: string | null;
  director?: string | null;
  actors?: string[];
}

export interface PersonShort {
  entity_id: number;
  entity_type: 'person';
  title: string;
  images: ImageURLs;
  is_director?: boolean;
  is_actor?: boolean;
}

export interface TaxonomyTerm {
  id: number;
  code: string | null;
  term_type: string;
  name: string;
}

export interface PersonRef {
  id: number;
  title: string;
  images: ImageURLs;
  role_type?: string | null;
  character_name?: string | null;
  billing_order?: number | null;
  title_en?: string | null;
  directed_count?: number | null;
  acted_count?: number | null;
  series_count?: number | null;
}

export interface FilmDetail {
  id: number;
  entity_type: 'film';
  title: string;
  original_title?: string | null;
  summary?: string | null;
  description?: string | null;
  release_year?: number | null;
  release_date?: string | null;
  runtime_min?: number | null;
  age_rating?: string | null;
  images: ImageURLs;
  backdrop_url?: string | null;
  stills_urls?: string[];
  genres?: TaxonomyTerm[];
  production_countries?: string | null;
  directors?: PersonRef[];
  cast?: PersonRef[];
  extra_metadata?: Record<string, unknown>;
  external_ids?: Record<string, string>;
}

export interface PersonAwardItem {
  status: 'won' | 'nominated';
  year: number;
  award_name: string;
  category_name?: string | null;
  film_title?: string | null;
}

export interface PersonAwardsBlock {
  wins_count: number;
  nominations_count: number;
  items: PersonAwardItem[];
}

export interface EntityDetail {
  id: number;
  entity_type: EntityType;
  title: string;
  summary?: string | null;
  description?: string | null;
  images: ImageURLs;
  language_code?: string;

  // Поля фильма
  release_year?: number | null;
  runtime_min?: number | null;
  rating_external?: number | null;

  // Поля персоны
  title_en?: string | null;
  is_director?: boolean;
  is_actor?: boolean;
  birth_date?: string | null;
  death_date?: string | null;
  birth_place?: string | null;
  primary_profession?: string | null;
  birth_year?: number | null;
  directed_count?: number | null;
  acted_count?: number | null;
  series_count?: number | null;
  crew_roles?: string[] | null;

  // Связанные сущности (если есть)
  filmography?: PersonFilmographyItem[];
  crew?: PersonShort[];
  genres?: string[];
  keywords?: string[];

  // Граф (только для персон)
  influenced_by?: PersonShort[];
  influenced?: PersonShort[];

  awards?: PersonAwardsBlock | null;
}

// ─── Рекомендации ────────────────────────────────
export type RecommendationMode = 'content' | 'semantic';

export interface RecommendationItem {
  entity_id: number;
  entity_type: EntityType;
  title: string;
  summary?: string | null;
  images: ImageURLs;
  release_year?: number | null;
  score: number;
  reasons: string[];
}

export interface RecommendationsResponse {
  items: RecommendationItem[];
  source_entity_id: number;
  source_entity_type: EntityType;
  algorithm: 'content_based' | 'semantic' | 'graph_based' | 'hybrid';
}

// ─── Коллекции ───────────────────────────────────
export interface CollectionItem {
  entity_id: number;
  entity_type: EntityType;
  title: string;
  summary?: string | null;
  images: ImageURLs;
  release_year?: number | null;
  position: number;
  note?: string | null;
}

export interface CollectionSummary {
  id: number;
  kind: 'custom' | 'editorial' | 'auto';
  title: string;
  summary?: string | null;
  cover_image?: string | null;
  items_count: number;
  is_featured: boolean;
  tags: string[];
}

export interface CollectionDetail extends CollectionSummary {
  description?: string | null;
  directors?: PersonRef[];
  items: CollectionItem[];
}

// ─── Статьи ──────────────────────────────────────
export type ArticleLinkType = 'about' | 'mentions' | 'reviews' | 'analyzes' | 'interview' | 'cites';

export interface ArticleEntityRef {
  entity_id: number;
  entity_type: EntityType;
  title: string;
  link_type: ArticleLinkType;
  images: ImageURLs;
}

export interface ArticleSummary {
  id: number;
  slug: string;
  article_type: string;
  title: string;
  summary?: string | null;
  cover_image?: string | null;
  reading_time_min?: number | null;
  is_featured: boolean;
  published_at?: string | null;
  main_subject?: ArticleEntityRef | null;
}

export interface ArticleDetail {
  id: number;
  slug: string;
  article_type: string;
  title: string;
  summary?: string | null;
  body?: string | null;
  cover_image?: string | null;
  reading_time_min?: number | null;
  is_featured: boolean;
  published_at?: string | null;
  author_name?: string | null;
  related_entities: ArticleEntityRef[];
}

// ─── Авторизация ─────────────────────────────────
export interface User {
  id: number;
  email: string;
  display_name: string;
  role?: string;
  avatar_url?: string | null;
  city?: string | null;
  preferred_language?: string | null;
  is_verified?: boolean;
  registered_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

// ─── Каталог ─────────────────────────────────────
export type FilmSortBy =
  | 'popularity'
  | 'vote_average'
  | 'year'
  | 'year_asc'
  | 'title';

export interface CatalogFilmCard {
  id: number;
  entity_type: 'film';
  title: string;
  original_title?: string | null;
  summary?: string | null;
  release_year?: number | null;
  runtime_min?: number | null;
  images: ImageURLs;
  genres: string[];
  director?: string | null;
  actors: string[];
  country?: string | null;
  vote_average?: number | null;
  popularity?: number | null;
}

export interface GenreItem {
  id: number;
  code: string | null;
  name: string;
  films_count: number;
}

// ─── Общее ───────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
