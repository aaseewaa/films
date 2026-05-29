import type { EntityDetail, PersonAwardItem } from '@/api/types';

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

function pluralYears(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'лет';
  if (mod10 === 1) return 'год';
  if (mod10 >= 2 && mod10 <= 4) return 'года';
  return 'лет';
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

function formatBirthDate(iso: string, opts?: { withAge?: boolean; deathDate?: string | null }): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  const day = parseInt(m[3], 10);
  const monthIdx = parseInt(m[2], 10) - 1;
  const year = parseInt(m[1], 10);
  if (monthIdx < 0 || monthIdx > 11 || day < 1) return null;
  let line = `${day} ${MONTHS_GENITIVE[monthIdx]} ${year}`;
  if (opts?.withAge && !opts.deathDate) {
    const age = ageFromIso(iso);
    if (age != null) line += ` (${age} ${pluralYears(age)})`;
  }
  return line;
}

function pluralWins(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'побед';
  if (mod10 === 1) return 'победа';
  if (mod10 >= 2 && mod10 <= 4) return 'победы';
  return 'побед';
}

function pluralNominations(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'номинаций';
  if (mod10 === 1) return 'номинация';
  if (mod10 >= 2 && mod10 <= 4) return 'номинации';
  return 'номинаций';
}

export function formatAwardsStatLine(
  wins: number,
  nominationsTotal: number,
): string | null {
  const parts: string[] = [];
  if (wins > 0) parts.push(`${wins} ${pluralWins(wins)}`);
  if (nominationsTotal > 0) {
    parts.push(`${nominationsTotal} ${pluralNominations(nominationsTotal)}`);
  }
  return parts.length > 0 ? parts.join(' · ') : null;
}

export function buildPersonFacts(person: EntityDetail): PersonFactRow[] {
  const rows: PersonFactRow[] = [];

  if (person.birth_date) {
    const formatted = formatBirthDate(person.birth_date, {
      withAge: true,
      deathDate: person.death_date,
    });
    if (formatted) rows.push({ label: 'Дата рождения', value: formatted });
  }

  if (person.death_date) {
    const formatted = formatBirthDate(person.death_date);
    if (formatted) rows.push({ label: 'Дата смерти', value: formatted });
  }

  if (person.birth_place?.trim()) {
    rows.push({ label: 'Место рождения', value: person.birth_place.trim() });
  }

  const awards = person.awards;
  if (awards) {
    const total = awards.wins_count + awards.nominations_count;
    const line = formatAwardsStatLine(awards.wins_count, total);
    if (line) rows.push({ label: 'Награды', value: line });
  }

  return rows;
}

export function formatAwardLine(item: PersonAwardItem): string {
  const parts = [String(item.year), item.award_name];
  if (item.category_name) parts.push(item.category_name);
  if (item.film_title) parts.push(`«${item.film_title}»`);
  return parts.join(' · ');
}
