import type { NewsFilmItem } from '@/api/news';

/** Постер из афиши (Кинопоиск / TMDB) — без него карточку не показываем */
export function hasAfishaPoster(film: NewsFilmItem): boolean {
  return Boolean(film.images.primary || film.images.thumbnail);
}
