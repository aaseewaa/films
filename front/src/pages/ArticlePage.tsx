import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getArticleBySlug } from '@/api/articles';
import {
  articleTypeLabel,
  authorForArticle,
  formatArticleDate,
  resolveImage,
  themeForSlug,
} from '@/lib/articleMosaic';
import { paragraphToNodes, splitArticleParagraphs } from '@/lib/articleBody';
import { cn } from '@/lib/utils';

export function ArticlePage() {
  const { slug } = useParams<{ slug: string }>();

  const { data: article, isLoading, error } = useQuery({
    queryKey: ['article', slug],
    queryFn: () => getArticleBySlug(slug!, 'ru'),
    enabled: !!slug,
  });

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50 bg-white">
        Загружаем статью…
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-page mx-auto px-6 py-24 text-center text-ink-50 bg-white">
        Статья не найдена
        <Link to="/articles" className="block mt-4 text-wine-500 hover:underline">
          ← К журналу
        </Link>
      </div>
    );
  }

  const heroImage = resolveImage(article);
  const theme = themeForSlug(article.slug);
  const typeLabel = articleTypeLabel(article.article_type);
  const dateStr = formatArticleDate(article.published_at);
  const author =
    article.author_name?.trim() ||
    authorForArticle(article, theme);
  const paragraphs = article.body ? splitArticleParagraphs(article.body) : [];
  const director = article.related_entities.find((r) => r.link_type === 'about');
  const frameBg = lightenFrame(theme.bg);

  return (
    <div className="bg-white min-h-screen">
      <div className="w-full max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10 pt-8 sm:pt-12 pb-20 sm:pb-28 text-center">
        <p className="text-left text-sm text-ink-50 mb-10 sm:mb-14">
          <Link to="/articles" className="hover:text-ink-300 transition-colors">
            ← Журнал
          </Link>
        </p>

        <header className="mb-10 sm:mb-14">
          <p className="font-sans text-[11px] sm:text-xs uppercase tracking-[0.22em] text-ink-50 mb-5">
            {typeLabel}
          </p>
          <h1 className="font-sans text-3xl sm:text-4xl lg:text-[2.75rem] font-bold leading-snug text-ink-400 max-w-[min(100%,56rem)] mx-auto">
            {article.title}
          </h1>
          <p className="font-sans text-lg sm:text-xl text-ink-300 mt-8 sm:mt-10">
            Автор: {author}
          </p>
          {dateStr && (
            <p className="font-mono text-sm sm:text-base text-ink-50 mt-3 tracking-wide">
              {dateStr}
            </p>
          )}
        </header>

        <figure
          className="w-full px-4 sm:px-8 lg:px-10 py-10 sm:py-14 lg:py-16 mb-12 sm:mb-16"
          style={{ backgroundColor: frameBg }}
        >
          {heroImage ? (
            <img
              src={heroImage}
              alt=""
              className="mx-auto w-full max-w-full max-h-[min(640px,68vh)] object-contain"
            />
          ) : (
            <div
              className="mx-auto w-full max-w-full aspect-[4/3] max-h-[min(480px,55vh)] opacity-30"
              style={{ backgroundColor: theme.bg }}
              aria-hidden
            />
          )}
        </figure>

        <article className="text-left w-full max-w-none mx-auto">
          {article.summary && (
            <p className="font-serif text-xl sm:text-2xl text-ink-300 leading-relaxed mb-12 sm:mb-14 text-center">
              {article.summary}
            </p>
          )}

          <div className="text-center sm:text-left space-y-8 sm:space-y-9">
            {paragraphs.map((para, idx) => (
              <p key={idx} className="font-serif text-xl sm:text-[1.35rem] lg:text-[1.5rem] leading-[1.85] text-ink-300">
                {paragraphToNodes(para)}
              </p>
            ))}
          </div>

          {paragraphs.length === 0 && !article.summary && (
            <p className="text-ink-50 text-center">Текст статьи пока не добавлен.</p>
          )}

          {director && (
            <aside className="mt-14 pt-10 border-t border-ink-50/15 text-center sm:text-left">
              <Link
                to={`/director/${director.entity_id}`}
                className="text-sm text-wine-500 hover:underline"
              >
                Карточка режиссёра: {director.title}
              </Link>
            </aside>
          )}
        </article>

        <footer className="mt-16 sm:mt-20 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/articles"
            className={cn(
              'inline-flex items-center justify-center px-8 py-3.5',
              'bg-ink-500 text-white text-sm font-medium uppercase tracking-wider',
              'hover:bg-ink-300 transition-colors',
            )}
          >
            К журналу
          </Link>
          <Link
            to="/"
            className="text-sm text-ink-50 hover:text-wine-500 transition-colors"
          >
            На главную
          </Link>
        </footer>
      </div>
    </div>
  );
}

/** Слегка осветляет цвет темы для «рамки» обложки, как на anothergaze.com */
function lightenFrame(hex: string): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return '#E8E4E8';
  const mix = (c: string) =>
    Math.min(255, Math.round(parseInt(c, 16) * 0.55 + 255 * 0.45));
  const r = mix(m[1]);
  const g = mix(m[2]);
  const b = mix(m[3]);
  return `rgb(${r}, ${g}, ${b})`;
}
