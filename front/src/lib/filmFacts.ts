import type { FilmDetail } from '@/api/types';

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

export interface FilmFactRow {
  label: string;
  value: string;
}

function formatPremiereDate(iso: string): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return null;
  const day = parseInt(m[3], 10);
  const monthIdx = parseInt(m[2], 10) - 1;
  const year = parseInt(m[1], 10);
  if (monthIdx < 0 || monthIdx > 11 || day < 1) return null;
  return `${day} ${MONTHS_GENITIVE[monthIdx]} ${year}`;
}

function formatUsd(amount: unknown): string | null {
  const n = Number(amount);
  if (!Number.isFinite(n) || n <= 0) return null;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n);
}

function formatRuntime(min: number): string {
  const mod10 = min % 10;
  const mod100 = min % 100;
  let word = 'минут';
  if (mod100 < 11 || mod100 > 14) {
    if (mod10 === 1) word = 'минута';
    else if (mod10 >= 2 && mod10 <= 4) word = 'минуты';
  }
  return `${min} ${word}`;
}

/** Строки для блока «Сведения» на странице фильма. */
export function buildFilmFacts(film: FilmDetail): FilmFactRow[] {
  const rows: FilmFactRow[] = [];

  if (film.production_countries?.trim()) {
    rows.push({ label: 'Страна', value: film.production_countries.trim() });
  }

  if (film.release_year) {
    rows.push({ label: 'Год', value: String(film.release_year) });
  }

  if (film.genres?.length) {
    rows.push({
      label: 'Жанры',
      value: film.genres.map((g) => g.name).join(', '),
    });
  }

  if (film.runtime_min != null && film.runtime_min > 0) {
    rows.push({ label: 'Время', value: formatRuntime(film.runtime_min) });
  }

  const premiere =
    (film.release_date && formatPremiereDate(film.release_date)) ||
    (film.release_year ? String(film.release_year) : null);
  if (premiere) {
    rows.push({ label: 'Премьера', value: premiere });
  }

  const budget = formatUsd(film.extra_metadata?.budget);
  if (budget) {
    rows.push({ label: 'Бюджет', value: budget });
  }

  return rows;
}
