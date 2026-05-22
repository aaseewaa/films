import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getFilmAfisha } from '@/api/news';
import { Button } from '@/components/ui/Button';

interface FilmCityAfishaProps {
  entityId: number;
  city: string;
}

export function FilmCityAfisha({ entityId, city }: FilmCityAfishaProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['news', 'film', entityId, city],
    queryFn: () => getFilmAfisha(entityId, city),
    enabled: entityId > 0 && !!city,
  });

  if (!isLoading && !isError && !data) {
    return null;
  }

  const hasAfisha =
    data &&
    (data.cinemas.length > 0 || Boolean(data.ticket_url));

  if (!isLoading && !isError && data && !hasAfisha) {
    return null;
  }

  return (
    <aside className="lg:sticky lg:top-40 self-start border border-ink-50/15 bg-site-bg hover:bg-site-hover p-5 sm:p-6 rounded-sm transition-colors">
      <p className="text-xs uppercase tracking-[0.18em] text-ink-50 mb-1">
        Афиша
      </p>
      <h3 className="font-serif text-xl font-bold text-ink-500 mb-4">
        В кино · {city}
      </h3>

      {isLoading && (
        <p className="text-sm text-ink-50">Загружаем сеансы…</p>
      )}

      {isError && (
        <p className="text-sm text-ink-100">
          Не удалось загрузить афишу. Попробуйте позже.
        </p>
      )}

      {data && (
        <>
          {data.cinemas.length > 0 ? (
            <ul className="space-y-2 mb-5 text-sm text-ink-300">
              {data.cinemas.map((name) => (
                <li key={name} className="flex gap-2">
                  <span className="text-wine-500">—</span>
                  {name}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-100 mb-5">
              Сеансы в вашем городе — на Кинопоиске. Нажмите «Купить билеты».
            </p>
          )}

          <a href={data.ticket_url} target="_blank" rel="noreferrer">
            <Button className="w-full" size="md">
              Купить билеты
            </Button>
          </a>

          <p className="mt-4 text-xs text-ink-50">
            <Link to="/news" className="text-wine-500 hover:underline">
              Все новинки в прокате
            </Link>
          </p>
        </>
      )}
    </aside>
  );
}
