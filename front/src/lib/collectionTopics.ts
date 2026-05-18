/** Быстрый поиск по темам — фильтр по тегам коллекций */
export interface CollectionTopic {
  id: string;
  label: string;
  /** only_featured через API */
  featuredOnly?: boolean;
}

export const COLLECTION_TOPICS: CollectionTopic[] = [
  { id: 'all', label: 'Все коллекции' },
  { id: 'featured', label: 'Избранные', featuredOnly: true },
  { id: 'auteur', label: 'Авторское кино' },
  { id: 'european-cinema', label: 'Европейское кино' },
  { id: 'classic', label: 'Классика' },
  { id: 'modern', label: 'Современное кино' },
  { id: 'psychological', label: 'Психологическое' },
  { id: 'east-asian', label: 'Восточная Азия' },
];

export type CollectionSort = 'popular' | 'title' | 'films_desc';

export const COLLECTION_SORT_OPTIONS: { value: CollectionSort; label: string }[] = [
  { value: 'popular', label: 'Популярные' },
  { value: 'films_desc', label: 'Больше фильмов' },
  { value: 'title', label: 'По алфавиту' },
];
