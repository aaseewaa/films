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

export type ArticleLayout = 'featured' | 'half' | 'quarter';

interface ArticleCardProps {
  article: ArticleSummary;
  layout?: ArticleLayout;
  className?: string;
}

/** Карточка журнала: фото + цветной блок (как на anothergaze.com) */
export function ArticleCard({ article, layout = 'quarter', className }: ArticleCardProps) {
  const theme = themeForSlug(article.slug);
  const imageUrl = resolveImage(article);
  const typeLabel = articleTypeLabel(article.article_type);
  const dateStr = formatArticleDate(article.published_at);
  const metaLine = [typeLabel, dateStr].filter(Boolean).join(' / ');
  const author = authorForArticle(article, theme);
  const light = theme.textLight;

  const metaClass = cn(
    'font-sans text-[10px] sm:text-[11px] uppercase tracking-[0.16em] font-medium',
    light ? 'text-white/80' : 'text-ink-500/70',
  );
  const titleClass = cn(
    'font-sans font-bold leading-[1.15]',
    layout === 'featured'
      ? 'text-lg sm:text-xl lg:text-[1.35rem]'
      : layout === 'half'
        ? 'text-sm sm:text-base'
        : 'text-base sm:text-lg',
    light ? 'text-white' : 'text-ink-500',
  );
  const bylineClass = cn(
    'font-sans text-xs sm:text-sm',
    light ? 'text-white/90' : 'text-ink-400',
  );
  const excerptClass = cn(
    'font-serif text-xs sm:text-sm leading-relaxed',
    layout === 'half' ? 'line-clamp-3' : 'line-clamp-4',
    light ? 'text-white/92' : 'text-ink-400',
  );

  const textBlock = (
    <>
      {metaLine && (
        <p className={cn(metaClass, layout === 'half' ? 'mb-1.5' : 'mb-2 sm:mb-3')}>
          {metaLine}
        </p>
      )}
      <h2 className={cn(titleClass, layout === 'half' ? 'mb-1' : 'mb-1.5')}>
        {article.title}
      </h2>
      <p className={cn(bylineClass, layout === 'half' ? 'mb-1.5' : 'mb-2')}>
        Автор: {author}
      </p>
      {article.summary && <p className={excerptClass}>{article.summary}</p>}
    </>
  );

  const imageAspect =
    layout === 'featured'
      ? 'aspect-[5/3] sm:aspect-[16/9]'
      : layout === 'half'
        ? 'min-h-[120px]'
        : 'aspect-[4/3] sm:aspect-square';

  const textPadding =
    layout === 'featured'
      ? 'p-4 sm:p-5 min-h-[130px] sm:min-h-[145px]'
      : layout === 'half'
        ? 'p-3 sm:p-4 min-h-[110px]'
        : 'p-4 sm:p-5 min-h-[150px] sm:min-h-[165px]';

  return (
    <Link
      to={`/article/${article.slug}`}
      className={cn(
        'group flex flex-col min-h-0 h-full hover:opacity-[0.98] transition-opacity',
        className,
      )}
    >
      <div
        className={cn(
          'relative w-full overflow-hidden bg-[#e8e6e1] shrink-0',
          layout === 'half' ? 'flex-1' : imageAspect,
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
          <ImageFallback bg={theme.bg} />
        )}
      </div>

      <div
        className={cn('flex flex-col shrink-0', textPadding)}
        style={{ backgroundColor: theme.bg }}
      >
        {textBlock}
      </div>
    </Link>
  );
}

function ImageFallback({ bg }: { bg: string }) {
  return (
    <div
      className="absolute inset-0 opacity-40"
      style={{ backgroundColor: bg }}
      aria-hidden
    />
  );
}
