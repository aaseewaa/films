import { Link } from 'react-router-dom';
import type { ArticleSummary } from '@/api/types';
import {
  articleTypeLabel,
  authorForArticle,
  formatArticleDate,
  resolveImage,
  themeForSlug,
} from '@/lib/articleMosaic';
import { cn } from '@/lib/utils';

/** Доля высоты карточки: фото / цветной блок */
export type ArticleSplit = '75-25' | '40-60' | '45-55' | '60-40';

interface ArticleCardProps {
  article: ArticleSummary;
  split?: ArticleSplit;
  className?: string;
}

export function ArticleCard({
  article,
  split = '40-60',
  className,
}: ArticleCardProps) {
  const theme = themeForSlug(article.slug);
  const imageUrl = resolveImage(article);
  const typeLabel = articleTypeLabel(article.article_type);
  const dateStr = formatArticleDate(article.published_at);
  const metaLine = [typeLabel, dateStr].filter(Boolean).join(' / ');
  const author = authorForArticle(article, theme);
  const light = theme.textLight;
  const wide = split === '75-25';
  const narrow = split === '40-60' || split === '45-55';
  const narrowTall = split === '45-55';
  const compact = split === '60-40';

  const metaClass = cn(
    'font-sans uppercase tracking-[0.16em] font-medium',
    wide
      ? 'text-[1.0625rem] sm:text-lg'
      : narrow
        ? 'text-xl sm:text-[1.375rem]'
        : 'text-xs sm:text-sm lg:text-[0.9375rem]',
    light ? 'text-white/80' : 'text-ink-500/70',
  );
  const titleClass = cn(
    'font-serif font-bold leading-[1.12]',
    wide
      ? 'text-[1.6875rem] sm:text-[1.875rem] lg:text-4xl'
      : narrow
        ? 'text-[1.75rem] sm:text-[2rem]'
        : 'text-base sm:text-lg lg:text-xl',
    light ? 'text-white' : 'text-ink-500',
  );
  const bylineClass = cn(
    'font-sans',
    wide
      ? 'text-xl sm:text-2xl'
      : narrow
        ? 'text-2xl sm:text-[1.75rem]'
        : 'text-sm sm:text-base lg:text-lg',
    light ? 'text-white/90' : 'text-ink-400',
  );
  const excerptClass = cn(
    'font-serif leading-relaxed',
    wide
      ? 'text-xl sm:text-2xl line-clamp-4'
      : narrow
        ? 'text-2xl sm:text-[1.75rem] line-clamp-3'
        : 'text-sm sm:text-base lg:text-lg line-clamp-4',
    light ? 'text-white/92' : 'text-ink-400',
  );

  const textPadding = wide ? 'p-5 sm:p-6' : narrow ? 'p-4 sm:p-5' : 'p-3 sm:p-4 lg:p-5';

  /** 75-25, 40-60, 45-55, 60-40 */
  const imageFlex = wide
    ? 'flex-[3]'
    : narrowTall
      ? 'flex-[4.5]'
      : narrow
        ? 'flex-[4]'
        : 'flex-[3]';
  const textFlex = wide
    ? 'flex-[1]'
    : narrowTall
      ? 'flex-[5.5]'
      : narrow
        ? 'flex-[6]'
        : 'flex-[2]';
  const textBottom = narrow || compact;

  return (
    <Link
      to={`/article/${article.slug}`}
      className={cn(
        'group flex flex-col h-full min-h-[300px] lg:min-h-0 hover:opacity-[0.98] transition-opacity',
        className,
      )}
    >
      <div className={cn('relative min-h-0 overflow-hidden bg-[#e8e6e1]', imageFlex)}>
        {imageUrl ? (
          <img
            src={imageUrl}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-top"
            loading="lazy"
          />
        ) : (
          <div
            className="absolute inset-0 opacity-40"
            style={{ backgroundColor: theme.bg }}
            aria-hidden
          />
        )}
      </div>

      <div
        className={cn(
          'flex flex-col shrink-0 min-h-0 overflow-hidden',
          textFlex,
          textBottom && 'justify-end',
          textPadding,
        )}
        style={{ backgroundColor: theme.bg }}
      >
        <div
          className={cn('flex flex-col min-h-0', textBottom && 'mt-auto max-h-full')}
        >
          {metaLine && (
            <p className={cn(metaClass, narrow ? 'mb-2 sm:mb-3' : 'mb-1 sm:mb-1.5')}>
              {metaLine}
            </p>
          )}
          <h2 className={cn(titleClass, narrow ? 'mb-2' : 'mb-1')}>{article.title}</h2>
          <p className={cn(bylineClass, narrow ? 'mb-2 sm:mb-3' : 'mb-1 sm:mb-1.5')}>
            Автор: {author}
          </p>
          {article.summary && <p className={excerptClass}>{article.summary}</p>}
        </div>
      </div>
    </Link>
  );
}
