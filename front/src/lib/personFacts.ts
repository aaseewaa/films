import type { EntityDetail, PersonAwardItem } from '@/api/types';
import { t } from '@/lib/i18n';
import { pluralNominations, pluralWins, pluralYears } from '@/lib/pluralize';
import { getSiteLang } from '@/lib/siteLang';
import type { SiteLocale } from '@/stores/locale';

const MONTHS_GENITIVE = [
  'января',
  'февраля',
  'марта',
  'апреля',
  'мая',
  'июня',
  'июля',
  'августа',
  'сентября',
  'октября',
  'ноября',
  'декабря',
] as const;

export interface PersonFactRow {
  label: string;
  value: string;
}

function ageFromIso(iso: string, asOf = new Date()): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  const birth = new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
  let age = asOf.getFullYear() - birth.getFullYear();
  const md = asOf.getMonth() - birth.getMonth();
  if (md < 0 || (md === 0 && asOf.getDate() < birth.getDate())) age -= 1;
  return age >= 0 ? age : null;
}

function formatBirthDate(
  iso: string,
  locale: SiteLocale,
  opts?: { withAge?: boolean; deathDate?: string | null },
): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  const day = parseInt(m[3], 10);
  const monthIdx = parseInt(m[2], 10) - 1;
  const year = parseInt(m[1], 10);
  if (monthIdx < 0 || monthIdx > 11 || day < 1) return null;

  let line =
    locale === 'en'
      ? new Date(year, monthIdx, day).toLocaleDateString('en-US', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        })
      : `${day} ${MONTHS_GENITIVE[monthIdx]} ${year}`;

  if (opts?.withAge && !opts.deathDate) {
    const age = ageFromIso(iso);
    if (age != null) line += ` (${age} ${pluralYears(age, locale)})`;
  }
  return line;
}

export function formatAwardsStatLine(
  wins: number,
  nominationsTotal: number,
  locale: SiteLocale = getSiteLang(),
): string | null {
  const parts: string[] = [];
  if (wins > 0) parts.push(`${wins} ${pluralWins(wins, locale)}`);
  if (nominationsTotal > 0) {
    parts.push(`${nominationsTotal} ${pluralNominations(nominationsTotal, locale)}`);
  }
  return parts.length > 0 ? parts.join(' · ') : null;
}

export function buildPersonFacts(
  person: EntityDetail,
  locale: SiteLocale = getSiteLang(),
): PersonFactRow[] {
  const rows: PersonFactRow[] = [];

  if (person.birth_date) {
    const formatted = formatBirthDate(person.birth_date, locale, {
      withAge: true,
      deathDate: person.death_date,
    });
    if (formatted) rows.push({ label: t(locale, 'factBirthDate'), value: formatted });
  }

  if (person.death_date) {
    const formatted = formatBirthDate(person.death_date, locale);
    if (formatted) rows.push({ label: t(locale, 'factDeathDate'), value: formatted });
  }

  if (person.birth_place?.trim()) {
    rows.push({ label: t(locale, 'factBirthPlace'), value: person.birth_place.trim() });
  }

  const awards = person.awards;
  if (awards) {
    const total = awards.wins_count + awards.nominations_count;
    const line = formatAwardsStatLine(awards.wins_count, total, locale);
    if (line) rows.push({ label: t(locale, 'factAwards'), value: line });
  }

  return rows;
}

export function formatAwardLine(item: PersonAwardItem): string {
  const parts = [String(item.year), item.award_name];
  if (item.category_name) parts.push(item.category_name);
  if (item.film_title) parts.push(`«${item.film_title}»`);
  return parts.join(' · ');
}
