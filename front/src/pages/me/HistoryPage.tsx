import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getHistory } from '@/api/userData';
import { PosterRow } from '@/components/profile/PosterRow';
import { ProfileLayout } from '@/components/profile/ProfileLayout';
import { useAuthStore } from '@/stores/auth';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function HistoryPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) navigate('/auth/login', { replace: true });
  }, [isAuthenticated, navigate]);

  const { data, isLoading } = useQuery({
    queryKey: ['history', 'all'],
    queryFn: () => getHistory(50),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) return null;

  const viewPosters =
    data?.views.map((v) => ({
      entity_id: v.entity_id,
      entity_type: v.entity_type,
      title: v.title,
      images: v.images,
    })) ?? [];

  return (
    <ProfileLayout title="История">
      {isLoading && <p className="text-ink-50">Загрузка…</p>}
      {data && (
        <div className="space-y-10">
          <section>
            <h2 className="text-sm sm:text-base lg:text-lg uppercase tracking-[0.16em] sm:tracking-[0.18em] text-ink-300 font-semibold mb-4">
              Просмотренные карточки
            </h2>
            <PosterRow
              items={viewPosters}
              emptyLabel="История просмотров пуста"
            />
            {data.views.length > 0 && (
              <ul className="mt-6 space-y-2">
                {data.views.map((v) => {
                  const path =
                    v.entity_type === 'person'
                      ? `/director/${v.entity_id}`
                      : `/film/${v.entity_id}`;
                  return (
                    <li key={`${v.entity_id}-${v.viewed_at}`}>
                      <Link
                        to={path}
                        className="flex justify-between text-sm text-wine-500 hover:underline"
                      >
                        <span className="truncate">{v.title}</span>
                        <span className="text-ink-50 text-xs shrink-0 ml-3">
                          {formatDate(v.viewed_at)}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section>
            <h2 className="text-sm sm:text-base lg:text-lg uppercase tracking-[0.16em] sm:tracking-[0.18em] text-ink-300 font-semibold mb-4">
              Поиски
            </h2>
            {data.searches.length === 0 ? (
              <p className="text-sm text-ink-50">Поисков пока нет</p>
            ) : (
              <ul className="divide-y divide-ink-50/15 rounded-sm border border-ink-50/20 bg-cream-50">
                {data.searches.map((s, i) => (
                  <li key={`${s.query_text}-${s.searched_at}-${i}`}>
                    <Link
                      to={`/search?q=${encodeURIComponent(s.query_text)}`}
                      className="flex justify-between px-4 py-3 hover:bg-site-hover text-sm transition-colors"
                    >
                      <span className="text-wine-500">{s.query_text}</span>
                      <span className="text-ink-50 text-xs">
                        {formatDate(s.searched_at)} · {s.results_count}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </ProfileLayout>
  );
}
