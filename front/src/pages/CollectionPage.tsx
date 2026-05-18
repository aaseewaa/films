import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Clapperboard } from 'lucide-react';
import { getCollection } from '@/api/collections';
import { cn } from '@/lib/utils';

function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

export function CollectionPage() {
  const { id } = useParams();
  const collectionId = id ? parseInt(id, 10) : 0;

  const { data: collection, isLoading, error } = useQuery({
    queryKey: ['collection', collectionId],
    queryFn: () => getCollection(collectionId, 'ru'),
    enabled: collectionId > 0,
  });

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50">
        Загружаем коллекцию…
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="max-w-page mx-auto px-6 py-24 text-center text-ink-50">
        Коллекция не найдена
        <Link to="/collections" className="block mt-4 text-wine-500 hover:underline">
          ← К списку коллекций
        </Link>
      </div>
    );
  }

  const films = collection.items.filter((i) => i.entity_type === 'film');
  const count = collection.items_count || films.length;

  return (
    <div className="bg-white min-h-screen">
      <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 pt-4 text-sm text-ink-50 max-w-[1920px] mx-auto">
        <Link to="/" className="hover:text-ink-300">
          Главная
        </Link>
        <span className="mx-2">»</span>
        <Link to="/collections" className="hover:text-ink-300">
          Коллекции
        </Link>
        <span className="mx-2">»</span>
        <span className="text-ink-300 line-clamp-1">{collection.title}</span>
      </div>

      <header className="max-w-page w-full mx-auto px-5 sm:px-10 lg:px-16 xl:px-20 py-8 sm:py-12">
        <div className="flex flex-col lg:flex-row gap-8 lg:gap-12">
          {collection.cover_image && (
            <img
              src={collection.cover_image}
              alt=""
              className="w-full lg:w-[min(48%,520px)] aspect-[16/10] object-cover shrink-0"
            />
          )}
          <div className="flex flex-col justify-center min-w-0">
            <p className="text-xs uppercase tracking-[0.14em] text-ink-50 mb-3">
              Коллекции
            </p>
            <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-ink-500 leading-[1.1] mb-4">
              {collection.title}
            </h1>
            <p className="flex items-center gap-2 text-lg text-ink-300 mb-4">
              <Clapperboard size={22} className="text-ink-50" strokeWidth={1.5} />
              {count} {pluralFilms(count)}
            </p>
            {collection.summary && (
              <p className="text-base sm:text-lg text-ink-300 leading-relaxed mb-4">
                {collection.summary}
              </p>
            )}
            {collection.description && collection.description !== collection.summary && (
              <p className="text-sm sm:text-base text-ink-50 leading-relaxed">
                {collection.description}
              </p>
            )}
          </div>
        </div>
      </header>

      <section className="max-w-page w-full mx-auto px-5 sm:px-10 lg:px-16 xl:px-20 pb-16 sm:pb-24">
        {films.length === 0 ? (
          <p className="text-ink-50 py-12 text-center">
            В подборке пока нет фильмов из каталога — они появятся после загрузки TMDB.
          </p>
        ) : (
          <ul className="divide-y divide-ink-50/15">
            {films.map((film) => (
              <li key={film.entity_id}>
                <Link
                  to={`/film/${film.entity_id}`}
                  className="flex items-center gap-6 sm:gap-10 py-8 sm:py-10 group"
                >
                  <div className="shrink-0 w-[100px] sm:w-[120px]">
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
                  <div className="min-w-0 flex-1">
                    <h2 className="text-xl sm:text-2xl font-bold text-ink-500 group-hover:text-ink-400 mb-1">
                      {film.title}
                    </h2>
                    {film.release_year && (
                      <p className="text-ink-50 text-sm sm:text-base">
                        {film.release_year} · фильм
                      </p>
                    )}
                    {film.note && (
                      <p className="text-ink-300 text-sm mt-2 line-clamp-2">{film.note}</p>
                    )}
                    {film.summary && (
                      <p className="text-ink-50 text-sm mt-2 line-clamp-2">{film.summary}</p>
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
              'hover:bg-ink-300 transition-colors',
            )}
          >
            К коллекциям
          </Link>
        </div>
      </section>
    </div>
  );
}
