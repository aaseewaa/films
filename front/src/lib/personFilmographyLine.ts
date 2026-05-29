export function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

function pluralSeries(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'сериалов';
  if (mod10 === 1) return 'сериал';
  if (mod10 >= 2 && mod10 <= 4) return 'сериала';
  return 'сериалов';
}

/** Строка «23 фильма | 8 сериалов» по данным из нашей БД. */
export function formatPersonWorkLine(
  person: {
    directed_count?: number | null;
    acted_count?: number | null;
    series_count?: number | null;
  },
  mode: 'director' | 'actor',
): string | null {
  const films = mode === 'director' ? person.directed_count : person.acted_count;
  const series = person.series_count ?? 0;
  const parts: string[] = [];

  if (films != null && films > 0) {
    parts.push(`${films} ${pluralFilms(films)}`);
  }
  if (series > 0) {
    parts.push(`${series} ${pluralSeries(series)}`);
  }

  return parts.length > 0 ? parts.join(' | ') : null;
}
