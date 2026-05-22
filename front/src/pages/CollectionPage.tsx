import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Clapperboard } from 'lucide-react';
import { getCollection } from '@/api/collections';
import { PageContent } from '@/components/layout/PageContent';
import { useSiteLang } from '@/lib/siteLang';
import { cn } from '@/lib/utils';

function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

const COVER_FRAME_BG = '#E4E8EC';

export function CollectionPage() {
  const lang = useSiteLang();
  const { id } = useParams();
  const collectionId = id ? parseInt(id, 10) : 0;

  const { data: collection, isLoading, error } = useQuery({
    queryKey: ['collection', collectionId, lang],
    queryFn: () => getCollection(collectionId),
    enabled: collectionId > 0,
  });

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50 bg-site-bg">
        Загружаем коллекцию…
      </div>
    );
  }

  if (error || !collection) {
    return (
      <PageContent className="py-24 text-center text-ink-50 bg-site-bg">
        Коллекция не найдена
        <Link to="/collections" className="block mt-4 text-wine-500 hover:underline">
          ← К списку коллекций
        </Link>
      </PageContent>
    );
  }

  const films = collection.items.filter((i) => i.entity_type === 'film');
  const count = collection.items_count || films.length;
  const directors = collection.directors ?? [];
  const bodyText =
    collection.description &&
    collection.description.trim() !== (collection.summary ?? '').trim()
      ? collection.description
      : null;

  return (
    <div className="bg-site-bg min-h-screen">
      <PageContent className="pt-8 sm:pt-12 pb-12 sm:pb-16 text-center">
        <p className="text-left text-base text-ink-50 mb-10 sm:mb-14">
          <Link to="/collections" className="hover:text-ink-300 transition-colors">
            ← Коллекции
          </Link>
        </p>

        <header className="mb-10 sm:mb-14 -mx-[max(1.25rem,6vw)] px-[max(1.25rem,6vw)]">
          <p className="font-sans text-base sm:text-lg uppercase tracking-[0.22em] text-ink-50 mb-5">
            Коллекции
          </p>
          <h1 className="font-sans text-3xl sm:text-4xl lg:text-[3.25rem] font-bold leading-snug text-ink-400 w-full max-w-[min(100%,72rem)] mx-auto text-balance">
            {collection.title}
          </h1>
          <p className="flex items-center justify-center gap-2 font-sans text-lg sm:text-xl text-ink-300 mt-6 sm:mt-8">
            <Clapperboard size={22} className="text-ink-50 shrink-0" strokeWidth={1.5} />
            {count} {pluralFilms(count)}
          </p>
        </header>

        {collection.cover_image && (
          <figure
            className="w-full px-4 sm:px-8 py-8 sm:py-12 mb-10 sm:mb-14"
            style={{ backgroundColor: COVER_FRAME_BG }}
          >
            <img
              src={collection.cover_image}
              alt=""
              className="mx-auto w-full max-w-[min(1280px,92vw)] max-h-[min(720px,96vh)] object-contain"
            />
          </figure>
        )}

        <div className="text-left w-full max-w-none mx-auto">
          {collection.summary && (
            <p className="font-serif text-lg sm:text-xl lg:text-2xl text-ink-300 leading-relaxed mb-6 sm:mb-8 text-center">
              {collection.summary}
            </p>
          )}

          {bodyText && (
            <p className="font-serif text-base sm:text-lg lg:text-xl leading-[1.78] text-ink-300 text-center sm:text-left mb-6 sm:mb-8">
              {bodyText}
            </p>
          )}

          {directors.length > 0 && (
            <aside className="pt-8 sm:pt-10 border-t border-ink-50/15 text-center">
              <p className="font-sans text-xs sm:text-sm uppercase tracking-[0.18em] text-ink-50 mb-4">
                Режиссёры
              </p>
              <p className="font-serif text-base sm:text-lg lg:text-xl text-ink-300 leading-relaxed">
                {directors.map((d, idx) => (
                  <span key={d.id}>
                    {idx > 0 && <span className="text-ink-50">, </span>}
                    <Link
                      to={`/director/${d.id}`}
                      className="text-ink-400 hover:text-wine-500 transition-colors underline-offset-2 hover:underline"
                    >
                      {d.title}
                    </Link>
                  </span>
                ))}
              </p>
            </aside>
          )}
        </div>
      </PageContent>

      <PageContent as="section" className="pb-16 sm:pb-24">
        {films.length === 0 ? (
          <p className="text-ink-50 py-12 text-center">
            В подборке пока нет фильмов из каталога — они появятся после загрузки TMDB.
          </p>
        ) : (
          <ul className="divide-y divide-ink-50/15 max-w-3xl sm:max-w-4xl lg:max-w-5xl mx-auto">
            {films.map((film) => (
              <li key={film.entity_id}>
                <Link
                  to={`/film/${film.entity_id}`}
                  className="collection-catalog-row flex items-center gap-8 sm:gap-10 lg:gap-12 py-10 sm:py-12 group transition-colors"
                >
                  <div className="shrink-0 w-[140px] sm:w-[180px] md:w-[210px]">
                    {film.images.primary ? (
                      <img
                        src={film.images.primary}
                        alt=""
                        className="w-full aspect-[2/3] object-cover bg-cream-200 group-hover:opacity-90 transition-opacity"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full aspect-[2/3] bg-cream-300" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1 flex flex-col justify-center py-2">
                    <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-ink-500 leading-[1.15] mb-2">
                      {film.title}
                    </h2>
                    {film.release_year && (
                      <p className="text-ink-50 text-sm sm:text-base mb-2">
                        {film.release_year} · фильм
                      </p>
                    )}
                    {film.note && (
                      <p className="text-ink-300 text-sm sm:text-base leading-relaxed line-clamp-3">
                        {film.note}
                      </p>
                    )}
                    {film.summary && (
                      <p className="text-ink-50 text-sm sm:text-base leading-relaxed mt-2 line-clamp-3">
                        {film.summary}
                      </p>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-12 flex justify-center">
          <Link
            to="/collections"
            className={cn(
              'inline-flex items-center justify-center px-8 py-4',
              'bg-ink-500 text-white text-sm font-medium uppercase tracking-wider',
              'hover:bg-site-hover transition-colors',
            )}
          >
            К коллекциям
          </Link>
        </div>
      </PageContent>
    </div>
  );
}
