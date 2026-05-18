import { Link } from 'react-router-dom';
import { Clapperboard } from 'lucide-react';
import type { CollectionSummary } from '@/api/types';

function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

interface CollectionCatalogCardProps {
  collection: CollectionSummary;
}

export function CollectionCatalogCard({ collection }: CollectionCatalogCardProps) {
  const count = collection.items_count;
  const countLabel =
    count === 0
      ? 'фильмы подбираются'
      : `${count} ${pluralFilms(count)}`;

  return (
    <article className="border-b border-ink-50/15 last:border-b-0">
      <Link
        to={`/collection/${collection.id}`}
        className="flex flex-col sm:flex-row sm:items-stretch gap-6 sm:gap-8 lg:gap-10 py-8 sm:py-10 lg:py-12 group"
      >
        <div className="shrink-0 w-full sm:w-[42%] lg:w-[44%] max-w-[520px]">
          {collection.cover_image ? (
            <img
              src={collection.cover_image}
              alt=""
              className="w-full aspect-[16/10] object-cover bg-ink-50/10 group-hover:opacity-92 transition-opacity"
              loading="lazy"
            />
          ) : (
            <div className="w-full aspect-[16/10] bg-cream-300 flex items-center justify-center text-ink-50 text-sm">
              Коллекция
            </div>
          )}
        </div>

        <div className="flex flex-col justify-center min-w-0 flex-1 py-1 sm:py-4">
          <p className="text-[11px] sm:text-xs uppercase tracking-[0.14em] text-ink-50 mb-3 sm:mb-4">
            Коллекции
          </p>
          <h2 className="font-serif text-2xl sm:text-3xl lg:text-[2rem] font-bold text-ink-500 leading-[1.12] mb-4 sm:mb-5 group-hover:text-ink-400 transition-colors">
            {collection.title}
          </h2>
          <p className="flex items-center gap-2 text-base sm:text-lg text-ink-300 mb-3">
            <Clapperboard size={20} className="shrink-0 text-ink-50" strokeWidth={1.5} />
            <span>{countLabel}</span>
          </p>
          {collection.summary && (
            <p className="text-sm sm:text-base text-ink-50 leading-relaxed line-clamp-3 max-w-xl">
              {collection.summary}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
