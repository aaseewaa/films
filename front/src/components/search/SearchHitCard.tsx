import { Link } from 'react-router-dom';
import type { SearchHit } from '@/api/types';
import { cn } from '@/lib/utils';

const MATCH_LABELS: Record<SearchHit['match_type'], string> = {
  fulltext: 'текст',
  fuzzy: 'похожее',
  exact: 'точное',
  semantic: 'смысл',
};

function entityPath(hit: SearchHit): string {
  if (hit.entity_type === 'person') return `/director/${hit.entity_id}`;
  return `/film/${hit.entity_id}`;
}

function entityKind(hit: SearchHit): string {
  if (hit.entity_type === 'film') return 'фильм';
  if (hit.is_director && hit.is_actor) return 'режиссёр · актёр';
  if (hit.is_director) return 'режиссёр';
  if (hit.is_actor) return 'актёр';
  return 'персона';
}

function formatScore(hit: SearchHit): string {
  const pct = Math.round(hit.score * 100);
  return hit.match_type === 'semantic' ? `${pct}%` : hit.score.toFixed(2);
}

interface SearchHitCardProps {
  hit: SearchHit;
}

export function SearchHitCard({ hit }: SearchHitCardProps) {
  const subtitle = [
    hit.release_year,
    entityKind(hit),
    hit.language_code?.toUpperCase(),
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <article className="border-b border-ink-50/15 last:border-b-0">
      <Link
        to={entityPath(hit)}
        className="flex items-start gap-8 sm:gap-10 lg:gap-12 py-10 sm:py-12 lg:py-14 group hover:bg-[rgba(10,186,181,0.08)] transition-colors"
      >
        <div className="shrink-0 w-[130px] sm:w-[160px] lg:w-[190px] xl:w-[220px]">
          {hit.images.primary || hit.images.thumbnail ? (
            <img
              src={hit.images.primary || hit.images.thumbnail || ''}
              alt=""
              className={cn(
                'w-full object-cover bg-ink-50/10 group-hover:opacity-90 transition-opacity',
                hit.entity_type === 'film' ? 'aspect-[2/3]' : 'aspect-square rounded-full',
              )}
              loading="lazy"
            />
          ) : (
            <div
              className={cn(
                'w-full bg-cream-300',
                hit.entity_type === 'film' ? 'aspect-[2/3]' : 'aspect-square rounded-full',
              )}
            />
          )}
        </div>

        <div className="min-w-0 flex-1 pt-2 sm:pt-3">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-3 sm:mb-4">
            <span className="text-xs sm:text-sm uppercase tracking-[0.16em] text-ink-50">
              {MATCH_LABELS[hit.match_type]}
            </span>
            <span className="text-xs sm:text-sm text-ink-50/80 tabular-nums">
              {formatScore(hit)}
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-ink-500 leading-snug mb-3 sm:mb-4 group-hover:text-ink-400 transition-colors">
            {hit.title}
          </h2>

          {subtitle && (
            <p className="text-base sm:text-lg text-ink-50 mb-3 sm:mb-4">{subtitle}</p>
          )}

          {hit.summary && (
            <p className="text-base sm:text-lg lg:text-xl text-ink-300 leading-relaxed line-clamp-4">
              {hit.summary}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
