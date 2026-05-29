import type { RatingBucket } from '@/api/userData';
import { cn } from '@/lib/utils';

interface RatingHistogramProps {
  buckets: RatingBucket[];
  total: number;
  average: number | null;
  /** Компактный вид для карточки «Активность» в профиле */
  compact?: boolean;
}

const MIN_BAR_PERCENT = 10;

function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

export function RatingHistogram({
  buckets,
  total,
  average,
  compact,
}: RatingHistogramProps) {
  const max = Math.max(...buckets.map((b) => b.count), 1);
  const rootClass = cn(compact && 'h-full flex flex-col min-h-0');

  return (
    <div className={rootClass}>
      {average != null && total > 0 && (
        <p
          className={cn(
            'text-ink-50 shrink-0',
            compact ? 'text-sm mb-3' : 'text-sm sm:text-base mb-4',
          )}
        >
          Средняя оценка{' '}
          <span className="text-ink-500 font-semibold tabular-nums">
            {average.toFixed(1).replace('.', ',')}
          </span>
          <span className="text-ink-50">
            {' '}
            · {total} {pluralFilms(total)}
          </span>
        </p>
      )}

      {total === 0 ? (
        <p
          className={cn(
            'text-sm text-ink-50 text-center',
            compact ? 'flex-1 flex items-center justify-center' : 'py-6',
          )}
        >
          Пока нет оценок — откройте фильм и поставьте балл от 1 до 10.
        </p>
      ) : (
        <div className={cn(compact && 'flex-1 flex flex-col justify-end min-h-0')}>
          <div
            className={cn(
              'relative flex items-end gap-0 w-full',
              compact ? 'flex-1 min-h-[4.5rem] max-h-full' : 'h-[5.5rem] sm:h-[6rem]',
            )}
            role="img"
            aria-label={`Распределение оценок: ${total} ${pluralFilms(total)}`}
          >
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-ink-50/35 z-10"
              aria-hidden
            />
            {buckets.map((b) => {
              const heightPercent =
                b.count > 0
                  ? Math.max(MIN_BAR_PERCENT, (b.count / max) * 100)
                  : 0;

              return (
                <div
                  key={b.rating}
                  className="relative flex-1 flex flex-col justify-end h-full min-w-0"
                  title={`${b.rating}: ${b.count}`}
                >
                  <div
                    className={cn(
                      'w-full transition-[height] duration-200',
                      b.count > 0
                        ? 'bg-tiffany hover:bg-tiffany-dark'
                        : 'bg-transparent',
                    )}
                    style={{ height: `${heightPercent}%` }}
                  />
                </div>
              );
            })}
          </div>

          <div className="mt-2 flex items-center justify-between text-[0.6875rem] sm:text-xs font-medium text-ink-50 tabular-nums">
            <span aria-hidden>1</span>
            <span className="sr-only">Шкала оценок от 1 до 10</span>
            <span aria-hidden>10</span>
          </div>
        </div>
      )}
    </div>
  );
}
