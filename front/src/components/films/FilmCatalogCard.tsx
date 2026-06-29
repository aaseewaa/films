import { Link } from 'react-router-dom';
import type { CatalogFilmCard } from '@/api/types';

function formatRating(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(1).replace('.', ',');
}

interface FilmCatalogCardProps {
  film: CatalogFilmCard;
}

export function FilmCatalogCard({ film }: FilmCatalogCardProps) {
  const subtitle = [
    film.original_title && film.original_title !== film.title
      ? film.original_title
      : null,
    film.release_year,
    'фильм',
  ]
    .filter(Boolean)
    .join(' / ');

  const genresCountry = [
    film.genres.length > 0 ? film.genres.join(', ') : null,
    film.country || null,
  ]
    .filter(Boolean)
    .join(' / ');

  const castLine = [
    film.director,
    film.actors.length > 0 ? film.actors.join(', ') : null,
  ]
    .filter(Boolean)
    .join(' / ');

  return (
    <article className="border-b border-ink-50/15 last:border-b-0">
      <Link
        to={`/film/${film.id}`}
        className="catalog-film-row flex items-center gap-6 sm:gap-8 lg:gap-10 py-8 sm:py-10 lg:py-12 group transition-colors"
      >
        <div className="shrink-0 w-[140px] sm:w-[180px] lg:w-[220px]">
          {film.images.primary ? (
            <img
              src={film.images.primary}
              alt={film.title}
              className="w-full aspect-[2/3] object-cover bg-ink-50/10 group-hover:opacity-90 transition-opacity"
              loading="lazy"
            />
          ) : (
            <div className="w-full aspect-[2/3] bg-cream-300" />
          )}
        </div>

        <div className="min-w-0 flex-1 flex flex-col justify-center py-2">
          <h2 className="catalog-film-title text-xl sm:text-2xl lg:text-[1.65rem] font-bold text-ink-500 leading-[1.15] mb-2 sm:mb-3 transition-colors">
            {film.title}
          </h2>

          {subtitle && (
            <p className="text-sm sm:text-base text-ink-50 mb-2 leading-snug">
              {subtitle}
            </p>
          )}

          {genresCountry && (
            <p className="text-sm sm:text-base text-ink-300 mb-2 leading-snug">
              {genresCountry}
            </p>
          )}

          {castLine && (
            <p className="text-sm sm:text-base text-ink-300 mb-3 sm:mb-4 leading-relaxed">
              {castLine}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm sm:text-base text-ink-300">
            {film.vote_average != null && (
              <span>
                <span className="text-ink-50">TMDB:</span>{' '}
                {formatRating(film.vote_average)}
              </span>
            )}
            {film.runtime_min != null && (
              <span className="text-ink-50">{film.runtime_min} мин</span>
            )}
          </div>
        </div>
      </Link>
    </article>
  );
}
