import type { PersonFilmographyItem } from '@/api/types';

export type BioTextSegment =
  | { kind: 'text'; value: string }
  | { kind: 'film'; value: string; filmId: number };

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function overlaps(
  start: number,
  end: number,
  occupied: Array<[number, number]>,
): boolean {
  return occupied.some(([s, e]) => start < e && end > s);
}

/** Упоминания фильмов из фильмографии → сегменты для ссылок на /film/{id}. */
export function splitBioTextWithFilmLinks(
  text: string,
  filmography: PersonFilmographyItem[],
): BioTextSegment[] {
  if (!text || filmography.length === 0) {
    return [{ kind: 'text', value: text }];
  }

  const byFilm = new Map<number, string[]>();
  for (const film of filmography) {
    const titles = byFilm.get(film.id) ?? [];
    const ru = film.title?.trim();
    const en = film.original_title?.trim();
    if (ru) titles.push(ru);
    if (en && en.toLowerCase() !== ru?.toLowerCase()) titles.push(en);
    byFilm.set(film.id, titles);
  }

  const patterns: { filmId: number; title: string }[] = [];
  for (const [filmId, titles] of byFilm) {
    for (const title of titles) {
      patterns.push({ filmId, title });
    }
  }
  patterns.sort((a, b) => b.title.length - a.title.length);

  const occupied: Array<[number, number]> = [];
  const matches: Array<{ start: number; end: number; filmId: number; value: string }> = [];

  for (const { filmId, title } of patterns) {
    const re = new RegExp(escapeRegExp(title), 'gi');
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const start = m.index;
      const end = start + m[0].length;
      if (overlaps(start, end, occupied)) continue;
      matches.push({ start, end, filmId, value: m[0] });
      occupied.push([start, end]);
    }
  }

  if (matches.length === 0) {
    return [{ kind: 'text', value: text }];
  }

  matches.sort((a, b) => a.start - b.start);

  const out: BioTextSegment[] = [];
  let cursor = 0;
  for (const hit of matches) {
    if (hit.start > cursor) {
      out.push({ kind: 'text', value: text.slice(cursor, hit.start) });
    }
    out.push({ kind: 'film', value: hit.value, filmId: hit.filmId });
    cursor = hit.end;
  }
  if (cursor < text.length) {
    out.push({ kind: 'text', value: text.slice(cursor) });
  }
  return out;
}
