import { useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { NewsFilmItem } from '@/api/news';
import { NewsFilmCard } from './NewsFilmCard';
import { cn } from '@/lib/utils';

interface NewsCarouselProps {
  title: string;
  films: NewsFilmItem[];
  metaLabel?: string;
}

export function NewsCarousel({
  title,
  films,
  metaLabel = 'СКОРО',
}: NewsCarouselProps) {
  const trackRef = useRef<HTMLDivElement>(null);

  function scroll(dir: -1 | 1) {
    const el = trackRef.current;
    if (!el) return;
    const step = el.clientWidth * 0.85;
    el.scrollBy({ left: dir * step, behavior: 'smooth' });
  }

  return (
    <section className="w-full">
      <div className="flex items-end justify-between gap-4 mb-4 sm:mb-6 px-5 sm:px-10 lg:px-16 xl:px-20 max-w-[1920px] mx-auto">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-ink-50 mb-1">
            Афиша
          </p>
          <h2 className="font-serif text-2xl sm:text-3xl font-bold text-ink-500">
            {title}
          </h2>
        </div>
        {films.length > 0 && (
          <div className="flex gap-2 shrink-0">
            <button
              type="button"
              onClick={() => scroll(-1)}
              className="p-2 border border-ink-50/20 text-ink-400 hover:bg-ink-50/5 rounded-sm"
              aria-label="Назад"
            >
              <ChevronLeft size={22} />
            </button>
            <button
              type="button"
              onClick={() => scroll(1)}
              className="p-2 border border-ink-50/20 text-ink-400 hover:bg-ink-50/5 rounded-sm"
              aria-label="Вперёд"
            >
              <ChevronRight size={22} />
            </button>
          </div>
        )}
      </div>

      {films.length === 0 ? (
        <p className="text-center text-ink-50 py-10 px-6">
          Премьеры временно недоступны.
        </p>
      ) : (
        <div
          ref={trackRef}
          className="flex gap-[3px] overflow-x-auto snap-x snap-mandatory px-[3px]"
        >
          {films.map((film, i) => (
            <div
              key={`${film.tmdb_id ?? film.title}-${i}`}
              className={cn(
                'snap-start shrink-0 w-[min(85vw,320px)] sm:w-[280px] md:w-[300px]',
              )}
            >
              <NewsFilmCard film={film} index={i} metaLabel={metaLabel} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
