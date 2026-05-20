import { Link } from 'react-router-dom';
import type { NewsFilmItem } from '@/api/news';
import { themeForIndex } from '@/lib/newsCardTheme';
import { cn } from '@/lib/utils';

interface NewsFilmCardProps {
  film: NewsFilmItem;
  index: number;
  metaLabel?: string;
  wide?: boolean;
}

export function NewsFilmCard({
  film,
  index,
  metaLabel = 'В ПРОКАТЕ',
  wide = false,
}: NewsFilmCardProps) {
  const theme = themeForIndex(index);
  const imageUrl = film.images.primary || film.images.thumbnail;
  const meta = [
    metaLabel,
    film.release_year ? String(film.release_year) : null,
  ]
    .filter(Boolean)
    .join(' / ');

  const href = film.entity_id ? `/film/${film.entity_id}` : film.ticket_url;
  const external = !film.entity_id;

  const content = (
    <>
      <div
        className={cn(
          'relative w-full overflow-hidden bg-[#e0e0e0]',
          wide ? 'aspect-[2/1]' : 'aspect-square',
        )}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-top"
            loading="lazy"
          />
        ) : (
          <div
            className="absolute inset-0 opacity-40"
            style={{ backgroundColor: theme.bg }}
            aria-hidden
          />
        )}
      </div>

      <div
        className="flex flex-col p-4 sm:p-5 md:p-6 min-h-[160px] flex-1"
        style={{ backgroundColor: theme.bg }}
      >
        {meta && (
          <p
            className={cn(
              'text-[10px] sm:text-[11px] uppercase tracking-[0.18em] font-medium mb-2 sm:mb-3',
              theme.textLight ? 'text-white/85' : 'text-ink-500/75',
            )}
          >
            {meta}
          </p>
        )}
        <h2
          className={cn(
            'font-serif font-bold leading-[1.2] mb-1.5 text-base sm:text-lg',
            theme.textLight ? 'text-white' : 'text-ink-500',
            wide && 'sm:text-xl md:text-2xl',
          )}
        >
          {film.title}
        </h2>
        <p
          className={cn(
            'text-xs sm:text-sm font-semibold mb-2',
            theme.textLight ? 'text-white/90' : 'text-ink-400',
          )}
        >
          {film.in_database ? 'В каталоге FilmCine' : 'Кинопрокат'}
        </p>
        {film.summary && (
          <p
            className={cn(
              'text-xs sm:text-sm leading-relaxed line-clamp-4',
              theme.textLight ? 'text-white/95' : 'text-ink-400',
            )}
          >
            {film.summary}
          </p>
        )}
      </div>
    </>
  );

  const className =
    'group flex flex-col min-h-0 hover:opacity-[0.97] transition-opacity h-full';

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className={className}
      >
        {content}
      </a>
    );
  }

  return (
    <Link to={href} className={className}>
      {content}
    </Link>
  );
}
