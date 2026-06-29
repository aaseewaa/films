import { Link } from 'react-router-dom';
import type { PersonFilmographyItem } from '@/api/types';
import { t } from '@/lib/i18n';
import { useSiteLang } from '@/lib/siteLang';

interface PersonFilmographyCardProps {
  film: PersonFilmographyItem;
}

export function PersonFilmographyCard({ film }: PersonFilmographyCardProps) {
  const locale = useSiteLang();
  const mediaKind = film.media_kind ?? t(locale, 'mediaFilm');
  const subtitle = [
    film.original_title && film.original_title !== film.title ? film.original_title : null,
    film.release_year,
    mediaKind,
  ]
    .filter(Boolean)
    .join(' / ');

  const genresCountry = [
    (film.genres?.length ?? 0) > 0 ? film.genres!.join(', ') : null,
    film.country || null,
  ]
    .filter(Boolean)
    .join(' / ');

  const crewLine = [
    film.director,
    (film.actors?.length ?? 0) > 0 ? film.actors!.join(', ') : null,
  ]
    .filter(Boolean)
    .join(' / ');

  return (
    <article className="border-b border-ink-50/15 last:border-b-0">
      <Link
        to={`/film/${film.id}`}
        className="flex items-center gap-8 sm:gap-10 lg:gap-12 py-10 sm:py-12 lg:py-14 group hover:bg-site-hover transition-colors"
      >
        <div className="shrink-0 w-[160px] sm:w-[200px] lg:w-[250px]">
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
          <h3 className="text-2xl sm:text-[1.65rem] lg:text-[2rem] font-bold text-ink-500 leading-[1.15] mb-3 sm:mb-4 group-hover:text-ink-400 transition-colors">
            {film.title}
          </h3>

          {subtitle && (
            <p className="text-base sm:text-lg text-ink-50 mb-2 sm:mb-2.5 leading-snug">{subtitle}</p>
          )}

          {genresCountry && (
            <p className="text-base sm:text-lg text-ink-300 mb-2 sm:mb-2.5 leading-snug">{genresCountry}</p>
          )}

          {crewLine && (
            <p className="text-base sm:text-lg text-ink-300 leading-relaxed">{crewLine}</p>
          )}
        </div>
      </Link>
    </article>
  );
}
