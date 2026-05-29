import { Link } from 'react-router-dom';
import type { ImageURLs } from '@/api/types';
import { cn } from '@/lib/utils';

export interface PosterItem {
  entity_id: number;
  entity_type: string;
  title: string;
  images: ImageURLs;
  release_year?: number | null;
  badge?: string | number;
}

interface PosterRowProps {
  items: PosterItem[];
  emptyLabel?: string;
  /** Ряд из 4 постеров — высота как у панели «Активность» в профиле */
  twinPanel?: boolean;
}

export function PosterRow({
  items,
  emptyLabel = 'Пусто',
  twinPanel,
}: PosterRowProps) {
  if (items.length === 0) {
    return (
      <p
        className={cn(
          'text-sm text-ink-50 text-center px-2',
          twinPanel
            ? 'h-full flex items-center justify-center'
            : 'py-4',
        )}
      >
        {emptyLabel}
      </p>
    );
  }

  return (
    <div
      className={cn(
        'grid gap-2 sm:gap-3',
        twinPanel
          ? 'grid-cols-4 h-full content-start'
          : 'grid-cols-4 sm:grid-cols-5 md:grid-cols-6',
      )}
    >
      {items.map((item) => {
        const path =
          item.entity_type === 'person'
            ? `/director/${item.entity_id}`
            : `/film/${item.entity_id}`;
        const img = item.images.thumbnail || item.images.primary;

        return (
          <Link
            key={item.entity_id}
            to={path}
            className="group relative aspect-[2/3] rounded-sm overflow-hidden bg-cream-200"
            title={item.title}
          >
            {img ? (
              <img
                src={img}
                alt={item.title}
                className="w-full h-full object-cover group-hover:opacity-90 transition-opacity"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center p-2 text-center text-[0.625rem] text-ink-50">
                {item.title}
              </div>
            )}
            {item.badge != null && (
              <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded-sm text-[0.625rem] font-bold bg-ink-500/90 text-white">
                {item.badge}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}
