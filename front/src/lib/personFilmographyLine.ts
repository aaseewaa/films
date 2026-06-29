import { getSiteLang } from '@/lib/siteLang';
import { pluralFilms, pluralSeries } from '@/lib/pluralize';
import type { SiteLocale } from '@/stores/locale';

export { pluralFilms, pluralSeries };

/** Строка «23 фильма | 8 сериалов» по данным из нашей БД. */
export function formatPersonWorkLine(
  person: {
    directed_count?: number | null;
    acted_count?: number | null;
    series_count?: number | null;
  },
  mode: 'director' | 'actor',
  locale: SiteLocale = getSiteLang(),
): string | null {
  const films = mode === 'director' ? person.directed_count : person.acted_count;
  const series = person.series_count ?? 0;
  const parts: string[] = [];

  if (films != null && films > 0) {
    parts.push(`${films} ${pluralFilms(films, locale)}`);
  }
  if (series > 0) {
    parts.push(`${series} ${pluralSeries(series, locale)}`);
  }

  return parts.length > 0 ? parts.join(' | ') : null;
}
