import type { PersonRef } from '@/api/types';
import { cn } from '@/lib/utils';

const PREVIEW_ACTORS_MAX = 6;

function splitInHalf<T>(items: T[]): [T[], T[]] {
  const mid = Math.ceil(items.length / 2);
  return [items.slice(0, mid), items.slice(mid)];
}

interface FilmCreatorsPreviewProps {
  directors: PersonRef[];
  cast: PersonRef[];
  onOpenAll?: () => void;
  /** Показать всех актёров, без кнопки «Смотреть все» */
  expanded?: boolean;
  className?: string;
}

/** Краткий блок «Создатели и актёры» на странице фильма. */
export function FilmCreatorsPreview({
  directors,
  cast,
  onOpenAll,
  expanded = false,
  className,
}: FilmCreatorsPreviewProps) {
  const hasDirectors = directors.length > 0;
  const hasCast = cast.length > 0;
  if (!hasDirectors && !hasCast) return null;

  const previewCast = expanded ? cast : cast.slice(0, PREVIEW_ACTORS_MAX);
  const showMoreLink = !expanded && !!onOpenAll;
  const [castColA, castColB] = splitInHalf(previewCast);
  return (
    <section className={cn(className)}>
      <h2 className="text-5xl sm:text-7xl lg:text-8xl font-bold text-ink-500 mb-6 sm:mb-8 leading-[1.05]">
        Создатели и актёры
      </h2>

      <div className="space-y-6 sm:space-y-8 text-2xl sm:text-3xl lg:text-4xl text-ink-500">
        {hasDirectors && (
          <div className="grid grid-cols-[minmax(6.5rem,auto)_1fr] sm:grid-cols-[minmax(7.5rem,auto)_1fr] gap-x-6 sm:gap-x-10 items-start">
            <span className="text-ink-50 pt-0.5 text-xl sm:text-2xl lg:text-3xl">Режиссёр</span>
            <p className="leading-snug">
              {directors.map((d) => d.title).join(', ')}
            </p>
          </div>
        )}

        {hasCast && (
          <div className="grid grid-cols-[minmax(6.5rem,auto)_1fr_1fr] sm:grid-cols-[minmax(7.5rem,auto)_1fr_1fr] gap-x-6 sm:gap-x-10 gap-y-1 items-start">
            <span className="text-ink-50 pt-0.5 row-span-full text-xl sm:text-2xl lg:text-3xl">
              Актёры
            </span>
            <ul className="space-y-1 leading-snug">
              {castColA.map((p) => (
                <li key={p.id}>{p.title}</li>
              ))}
            </ul>
            <ul className="space-y-1 leading-snug">
              {castColB.map((p) => (
                <li key={p.id}>{p.title}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {showMoreLink && (
        <button
          type="button"
          onClick={onOpenAll}
          className="mt-8 sm:mt-10 text-xl sm:text-2xl text-ink-50 hover:text-ink-400 transition-colors"
        >
          Смотреть все →
        </button>
      )}
    </section>
  );
}
