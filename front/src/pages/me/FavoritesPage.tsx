import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getFavorites } from '@/api/userData';
import { PosterRow } from '@/components/profile/PosterRow';
import { ProfileLayout } from '@/components/profile/ProfileLayout';
import { useAuthStore } from '@/stores/auth';

const STATUS_LABEL: Record<string, string> = {
  want_to_watch: 'Хочу посмотреть',
  watching: 'Смотрю',
  watched: 'Просмотрено',
  dropped: 'Брошено',
};

export function FavoritesPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) navigate('/auth/login', { replace: true });
  }, [isAuthenticated, navigate]);

  const { data, isLoading } = useQuery({
    queryKey: ['favorites', 'all'],
    queryFn: () => getFavorites({ limit: 100 }),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) return null;

  return (
    <ProfileLayout title="Избранное">
      {isLoading && <p className="text-ink-50">Загрузка…</p>}
      {data && (
        <>
          <p className="text-sm text-ink-50 mb-6">{data.total} в списке</p>
          {data.items.length === 0 ? (
            <p className="text-ink-50 text-center py-12">Избранное пусто</p>
          ) : (
            <>
              <PosterRow
                items={data.items.map((item) => ({
                  entity_id: item.entity_id,
                  entity_type: item.entity_type,
                  title: item.title,
                  images: item.images,
                  release_year: item.release_year,
                }))}
              />
              <ul className="mt-8 divide-y divide-ink-50/15 rounded-sm border border-ink-50/20 bg-cream-50">
                {data.items.map((item) => (
                  <li
                    key={item.entity_id}
                    className="flex justify-between px-4 py-3 text-sm"
                  >
                    <span className="text-ink-500">{item.title}</span>
                    <span className="text-ink-50 text-xs">
                      {STATUS_LABEL[item.status] ?? item.status}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </ProfileLayout>
  );
}
