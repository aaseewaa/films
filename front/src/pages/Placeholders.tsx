import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getEntity } from '@/api/entity';

export function DirectorPage() {
  const { id } = useParams();
  const directorId = id ? parseInt(id, 10) : 0;

  const { data, isLoading, error } = useQuery({
    queryKey: ['entity', directorId],
    queryFn: () => getEntity(directorId),
    enabled: !!directorId,
  });

  if (isLoading) return <Placeholder>Загружаем режиссёра...</Placeholder>;
  if (error || !data) return <Placeholder>Не удалось загрузить</Placeholder>;

  return (
    <div className="max-w-page mx-auto px-4 sm:px-6 py-12">
      <Link to="/" className="text-sm text-wine-500 hover:underline mb-6 inline-block">
        ← Назад к графу
      </Link>

      <div className="grid md:grid-cols-[1fr_auto] gap-12 mb-12">
        <div>
          <h1 className="font-serif text-display mb-4">{data.title}</h1>
          {data.description && (
            <p className="prose-essay">{data.description}</p>
          )}
        </div>

        {data.images.primary && (
          <img
            src={data.images.primary}
            alt={data.title}
            className="w-64 h-96 object-cover rounded-sm"
          />
        )}
      </div>

      {data.filmography && data.filmography.length > 0 && (
        <section className="mt-12">
          <h2 className="font-serif text-h2 mb-6">Фильмография</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {data.filmography.map((film) => (
              <Link
                key={film.entity_id}
                to={`/film/${film.entity_id}`}
                className="group"
              >
                {film.images.primary ? (
                  <img
                    src={film.images.primary}
                    alt={film.title}
                    className="w-full aspect-[2/3] object-cover rounded-sm group-hover:opacity-80 transition-opacity"
                  />
                ) : (
                  <div className="w-full aspect-[2/3] bg-cream-300 rounded-sm" />
                )}
                <p className="mt-2 text-sm font-medium text-ink-300 line-clamp-2">
                  {film.title}
                </p>
                {film.release_year && (
                  <p className="text-xs text-ink-50">{film.release_year}</p>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export function SearchPage() {
  return <Placeholder>Страница поиска — день 3 (16 мая)</Placeholder>;
}

export function NewsPage() {
  return <Placeholder>Новинки — день 6</Placeholder>;
}

export function LoginPage() {
  return <Placeholder>Логин — день 4 (17 мая)</Placeholder>;
}

export function RegisterPage() {
  return <Placeholder>Регистрация — день 4 (17 мая)</Placeholder>;
}

export function ProfilePage() {
  return <Placeholder>Профиль — день 4</Placeholder>;
}

export function FavoritesPage() {
  return <Placeholder>Избранное — день 4</Placeholder>;
}

export function RatingsPage() {
  return <Placeholder>Мои оценки — день 4</Placeholder>;
}

export function HistoryPage() {
  return <Placeholder>История — день 4</Placeholder>;
}

export function NotFoundPage() {
  return (
    <Placeholder>
      <span className="text-h1 font-serif block mb-4">404</span>
      Страницы не существует
      <br />
      <Link to="/" className="text-wine-500 hover:underline mt-4 inline-block">
        ← На главную
      </Link>
    </Placeholder>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-page mx-auto px-4 sm:px-6 py-24">
      <div className="text-center text-ink-100">
        <div className="font-serif text-2xl">{children}</div>
      </div>
    </div>
  );
}
