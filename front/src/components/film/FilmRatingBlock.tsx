import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getEntityRatingStats,
  getMyRating,
  setRating,
} from '@/api/ratings';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

interface FilmRatingBlockProps {
  entityId: number;
  /** Крупные подписи и квадраты оценки (страница фильма). */
  large?: boolean;
}

function formatAvg(v: number | null | undefined): string | null {
  if (v == null || Number.isNaN(v)) return null;
  return v.toFixed(1).replace('.', ',');
}

function pluralRatings(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'оценок';
  if (mod10 === 1) return 'оценка';
  if (mod10 >= 2 && mod10 <= 4) return 'оценки';
  return 'оценок';
}

export function FilmRatingBlock({ entityId, large }: FilmRatingBlockProps) {
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [hoverScore, setHoverScore] = useState<number | null>(null);

  const { data: myRating } = useQuery({
    queryKey: ['rating', 'me', entityId],
    queryFn: () => getMyRating(entityId),
    enabled: isAuthenticated && entityId > 0,
  });

  const { data: stats } = useQuery({
    queryKey: ['rating', 'stats', entityId],
    queryFn: () => getEntityRatingStats(entityId),
    enabled: entityId > 0,
  });

  const rateMutation = useMutation({
    mutationFn: (score: number) => setRating(entityId, score),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rating', 'me', entityId] });
      queryClient.invalidateQueries({ queryKey: ['rating', 'stats', entityId] });
    },
  });

  const activeScore = hoverScore ?? myRating?.rating ?? null;
  const communityAvg = formatAvg(stats?.avg_rating);
  const totalRatings = stats?.total_ratings ?? 0;

  function handlePick(score: number) {
    if (!isAuthenticated) return;
    rateMutation.mutate(score);
  }

  return (
    <div className="mb-8">
      <div
        className="flex gap-1 mb-3"
        role={isAuthenticated ? 'radiogroup' : undefined}
        aria-label="Оценка фильма от 1 до 10"
        onMouseLeave={() => setHoverScore(null)}
      >
        {Array.from({ length: 10 }, (_, i) => {
          const score = i + 1;
          const filled = activeScore != null && score <= activeScore;
          return (
            <button
              key={score}
              type="button"
              disabled={!isAuthenticated || rateMutation.isPending}
              onMouseEnter={() => isAuthenticated && setHoverScore(score)}
              onClick={() => handlePick(score)}
              aria-label={`Оценка ${score}`}
              aria-pressed={myRating?.rating === score}
              className={cn(
                large ? 'w-12 h-12 sm:w-14 sm:h-14' : 'w-8 h-8 sm:w-9 sm:h-9',
                'border rounded-sm transition-colors',
                'disabled:cursor-default',
                isAuthenticated && 'cursor-pointer hover:border-ink-400',
                filled
                  ? 'bg-ink-500 border-ink-500'
                  : 'border-ink-50/25 bg-site-bg hover:bg-site-hover',
              )}
            />
          );
        })}
      </div>

      {!isAuthenticated && (
        <p className={cn(large ? 'text-lg sm:text-xl' : 'text-sm', 'text-ink-50 mb-2')}>
          <Link to="/auth/login" className="text-wine-500 hover:underline">
            Войдите
          </Link>
          , чтобы поставить оценку.
        </p>
      )}

      {isAuthenticated && rateMutation.isError && (
        <p className={cn(large ? 'text-lg sm:text-xl' : 'text-sm', 'text-wine-500 mb-2')}>
          Не удалось сохранить оценку. Попробуйте ещё раз.
        </p>
      )}

      {myRating && (
        <p className={cn(large ? 'text-xl sm:text-2xl' : 'text-base', 'text-ink-300 mb-2')}>
          Ваша оценка:{' '}
          <span className="font-semibold text-ink-500">{myRating.rating}</span>
        </p>
      )}

      {communityAvg && totalRatings > 0 && (
        <p className={cn(large ? 'text-xl sm:text-2xl' : 'text-base', 'text-ink-300')}>
          Средняя оценка пользователей:{' '}
          <span className="font-semibold text-ink-500">{communityAvg}</span>
          <span className="text-ink-50">
            {' '}
            ({totalRatings} {pluralRatings(totalRatings)})
          </span>
        </p>
      )}
    </div>
  );
}
