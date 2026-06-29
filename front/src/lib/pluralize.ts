import { t } from '@/lib/i18n';
import type { SiteLocale } from '@/stores/locale';

/** Русская форма: 1 / 2–4 / 5+ (11–14 → many). */
export function pluralSlavic(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return many;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

export function pluralFilms(n: number, locale: SiteLocale): string {
  if (locale === 'en') return n === 1 ? t(locale, 'mediaFilm') : t(locale, 'mediaFilms');
  return pluralSlavic(
    n,
    t(locale, 'mediaFilm'),
    t(locale, 'pluralFilmFew'),
    t(locale, 'pluralFilmMany'),
  );
}

export function pluralSeries(n: number, locale: SiteLocale): string {
  if (locale === 'en') return t(locale, 'mediaSeries');
  return pluralSlavic(
    n,
    t(locale, 'mediaSeries'),
    t(locale, 'pluralSeriesFew'),
    t(locale, 'pluralSeriesMany'),
  );
}

export function pluralYears(n: number, locale: SiteLocale): string {
  if (locale === 'en') return n === 1 ? t(locale, 'pluralYearOne') : t(locale, 'pluralYearMany');
  return pluralSlavic(
    n,
    t(locale, 'pluralYearOne'),
    t(locale, 'pluralYearFew'),
    t(locale, 'pluralYearMany'),
  );
}

export function pluralWins(n: number, locale: SiteLocale): string {
  if (locale === 'en') return n === 1 ? t(locale, 'pluralWinOne') : t(locale, 'pluralWinMany');
  return pluralSlavic(
    n,
    t(locale, 'pluralWinOne'),
    t(locale, 'pluralWinFew'),
    t(locale, 'pluralWinMany'),
  );
}

export function pluralNominations(n: number, locale: SiteLocale): string {
  if (locale === 'en') {
    return n === 1 ? t(locale, 'pluralNominationOne') : t(locale, 'pluralNominationMany');
  }
  return pluralSlavic(
    n,
    t(locale, 'pluralNominationOne'),
    t(locale, 'pluralNominationFew'),
    t(locale, 'pluralNominationMany'),
  );
}
