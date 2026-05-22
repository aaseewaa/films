import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMyRatings, getRatingDistribution } from '@/api/userData';
import { ProfileLayout } from '@/components/profile/ProfileLayout';
import { RatingHistogram } from '@/components/profile/RatingHistogram';
import { useAuthStore } from '@/stores/auth';

export function RatingsPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) navigate('/auth/login', { replace: true });
  }, [isAuthenticated, navigate]);

  const ratingsQ = useQuery({
    queryKey: ['ratings', 'all'],
    queryFn: () => getMyRatings({ limit: 100 }),
    enabled: isAuthenticated,
  });

  const distQ = useQuery({
    queryKey: ['profile', 'distribution'],
    queryFn: getRatingDistribution,
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) return null;

  return (
    <ProfileLayout title="Мои оценки">
      {distQ.data && (
        <div className="mb-10 rounded-sm bg-cream-50 border border-ink-50/20 p-5">
          <RatingHistogram
            buckets={distQ.data.buckets}
            total={distQ.data.total}
            average={distQ.data.average}
          />
        </div>
      )}

      {ratingsQ.isLoading && <p className="text-ink-50">Загрузка…</p>}
      {ratingsQ.data && (
        <ul className="divide-y divide-ink-50/15 rounded-sm border border-ink-50/20 overflow-hidden bg-cream-50">
          {ratingsQ.data.items.map((item) => {
            const path =
              item.entity_type === 'person'
                ? `/director/${item.entity_id}`
                : `/film/${item.entity_id}`;
            const img = item.images.thumbnail || item.images.primary;

            return (
              <li key={item.entity_id}>
                <Link
                  to={path}
                  className="flex items-center gap-4 p-4 hover:bg-site-hover transition-colors"
                >
                  <div className="w-12 h-[4.5rem] shrink-0 rounded-sm overflow-hidden bg-cream-200">
                    {img ? (
                      <img src={img} alt="" className="w-full h-full object-cover" />
                    ) : null}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-ink-500 font-medium truncate">{item.title}</p>
                    {item.release_year && (
                      <p className="text-xs text-ink-50">{item.release_year}</p>
                    )}
                  </div>
                  <span className="text-2xl font-bold text-wine-500 tabular-nums">
                    {item.rating}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      {ratingsQ.data?.items.length === 0 && (
        <p className="text-ink-50 text-center py-12">Оценок пока нет</p>
      )}
    </ProfileLayout>
  );
}
