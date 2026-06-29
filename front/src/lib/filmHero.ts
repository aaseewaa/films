import type { FilmDetail } from '@/api/types';

function imageBasename(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) return null;
  const name = trimmed.split('/').pop()?.split('?')[0];
  return name || null;
}

function isSameImage(left: string | null | undefined, right: string | null | undefined): boolean {
  if (!left || !right) return false;
  const leftName = imageBasename(left);
  const rightName = imageBasename(right);
  return Boolean(leftName && rightName && leftName === rightName);
}

/** Кадр для hero страницы фильма. Афишу не используем — только backdrop/stills. */
export function resolveFilmHeroImage(film: FilmDetail): string | null {
  const poster = film.images.primary || film.images.thumbnail || null;
  const candidates = [film.backdrop_url, ...(film.stills_urls ?? [])];

  for (const url of candidates) {
    if (url && !isSameImage(url, poster)) {
      return url;
    }
  }

  return null;
}
