import { Link } from 'react-router-dom';
import type { ArticleSummary } from '@/api/types';
import {
  articleTypeLabel,
  formatArticleDate,
  resolveImage,
  themeForSlug,
} from '@/lib/articleMosaic';
import { cn } from '@/lib/utils';

interface ArticleCardProps {
  article: ArticleSummary;
  variant?: 'grid' | 'stack';
}

/** Фото сверху (без текста) + цветной блок снизу */
export function ArticleCard({ article, variant = 'grid' }: ArticleCardProps) {
  const theme = themeForSlug(article.slug);
  const wide = theme.colSpan === 2;
  const imageUrl = resolveImage(article);
  const typeLabel = articleTypeLabel(article.article_type);
  const dateStr = formatArticleDate(article.published_at);
  const metaLine = [typeLabel, dateStr].filter(Boolean).join(' / ');
  const light = theme.textLight;
  const byline = article.main_subject?.title
    ? `О ${article.main_subject.title}`
    : 'Редакция';

  return (
    <Link
      to={`/article/${article.slug}`}
      className={cn(
        'group flex flex-col min-h-0 hover:opacity-[0.97] transition-opacity',
        variant === 'grid' && wide && 'lg:col-span-2',
      )}
    >
      <div
        className={cn(
          'relative w-full overflow-hidden bg-[#e0e0e0]',
          wide ? 'aspect-[2/1]' : 'aspect-square',
        )}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-top"
            loading="lazy"
          />
        ) : (
          <div
            className="absolute inset-0 opacity-35"
            style={{ backgroundColor: theme.bg }}
            aria-hidden
          />
        )}
      </div>

      <div
        className="flex flex-col p-4 sm:p-5 md:p-6 min-h-[160px] flex-1"
        style={{ backgroundColor: theme.bg }}
      >
        {metaLine && (
          <p
            className={cn(
              'text-[10px] sm:text-[11px] uppercase tracking-[0.18em] font-medium mb-2 sm:mb-3',
              light ? 'text-white/85' : 'text-ink-500/75',
            )}
          >
            {metaLine}
          </p>
        )}
        <h2
          className={cn(
            'font-serif font-bold leading-[1.2] mb-1.5',
            wide ? 'text-lg sm:text-xl md:text-2xl' : 'text-base sm:text-lg',
            light ? 'text-white' : 'text-ink-500',
          )}
        >
          {article.title}
        </h2>
        <p
          className={cn(
            'text-xs sm:text-sm font-semibold mb-2',
            light ? 'text-white/90' : 'text-ink-400',
          )}
        >
          {byline}
        </p>
        {article.summary && (
          <p
            className={cn(
              'text-xs sm:text-sm leading-relaxed line-clamp-4',
              light ? 'text-white/95' : 'text-ink-400',
            )}
          >
            {article.summary}
          </p>
        )}
      </div>
    </Link>
  );
}
