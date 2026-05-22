import { Link } from 'react-router-dom';
import type { FilmDetail } from '@/api/types';
import type { RecommendationItem } from '@/api/types';
import { FilmCreatorsPreview } from '@/components/film/FilmCreatorsPreview';

export function FilmStillsPanel({ film }: { film: FilmDetail }) {
  if (!film.stills_urls?.length) {
    return (
      <p className="text-xl sm:text-2xl lg:text-3xl text-ink-50">
        Кадры ещё не загружены. Запустите{' '}
        <code className="text-lg bg-cream-200 px-1.5">load_tmdb_images</code> на бэке.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
      {film.stills_urls.map((url, i) => (
        <a
          key={url}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="block overflow-hidden bg-cream-200 hover:opacity-90 transition-opacity"
        >
          <img
            src={url}
            alt={`Кадр ${i + 1}`}
            className="w-full aspect-video object-cover"
            loading="lazy"
          />
        </a>
      ))}
    </div>
  );
}

export function FilmArticlesPanel() {
  return (
    <p className="text-xl sm:text-2xl lg:text-3xl text-ink-50">
      <Link to="/articles" className="text-wine-500 hover:underline">
        Журнал
      </Link>{' '}
      — скоро материалы об этом фильме.
    </p>
  );
}

export function FilmSimilarPanel({ items }: { items: RecommendationItem[] }) {
  if (!items.length) {
    return <p className="text-xl sm:text-2xl lg:text-3xl text-ink-50">Пока нет рекомендаций.</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5 sm:gap-8">
      {items.map((item) => (
        <Link key={item.entity_id} to={`/film/${item.entity_id}`} className="group">
          {item.images.primary ? (
            <img
              src={item.images.primary}
              alt={item.title}
              className="w-full aspect-[2/3] object-cover group-hover:opacity-85 transition-opacity"
            />
          ) : (
            <div className="aspect-[2/3] bg-cream-300" />
          )}
          <p className="mt-3 text-lg sm:text-xl lg:text-2xl font-medium text-ink-400 line-clamp-2 group-hover:text-ink-500">
            {item.title}
          </p>
        </Link>
      ))}
    </div>
  );
}

export function FilmAwardsPanel() {
  return (
    <p className="text-xl sm:text-2xl lg:text-3xl text-ink-50">Информация о наградах появится позже.</p>
  );
}

interface FilmCreatorsTeaserProps {
  directors: FilmDetail['directors'];
  cast: FilmDetail['cast'];
  onOpenAll: () => void;
}

export function FilmCreatorsTeaser({ directors, cast, onOpenAll }: FilmCreatorsTeaserProps) {
  const d = directors ?? [];
  const c = cast ?? [];
  if (!d.length && !c.length) return null;

  return (
    <div className="mt-16 sm:mt-20 pt-12 border-t border-ink-50/15">
      <FilmCreatorsPreview directors={d} cast={c} onOpenAll={onOpenAll} />
    </div>
  );
}
