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
        className="flex items-start gap-6 sm:gap-8 lg:gap-10 py-8 sm:py-10 group"
      >
        <div className="shrink-0 w-[100px] sm:w-[120px] lg:w-[140px]">
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

        <div className="min-w-0 flex-1 pt-1">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-[10px] uppercase tracking-[0.16em] text-ink-50">
              {MATCH_LABELS[hit.match_type]}
            </span>
            <span className="text-[10px] text-ink-50/80 tabular-nums">
              {formatScore(hit)}
            </span>
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-ink-500 leading-snug mb-2 group-hover:text-ink-400 transition-colors">
            {hit.title}
          </h2>

          {subtitle && (
            <p className="text-sm text-ink-50 mb-2">{subtitle}</p>
          )}

          {hit.summary && (
            <p className="text-sm sm:text-base text-ink-300 leading-relaxed line-clamp-3">
              {hit.summary}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
