import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getArticleBySlug } from '@/api/articles';
import {
  articleTypeLabel,
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
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50">
        Загружаем статью…
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-page mx-auto px-6 py-24 text-center text-ink-50">
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
  const metaLine = [typeLabel, dateStr].filter(Boolean).join(' / ');
  const paragraphs = article.body ? splitArticleParagraphs(article.body) : [];
  const director = article.related_entities.find((r) => r.link_type === 'about');

  return (
    <div className="bg-white min-h-screen">
      <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 pt-4 text-sm sm:text-base text-ink-50 max-w-[1920px] mx-auto">
        <Link to="/" className="hover:text-ink-300">
          Главная
        </Link>
        <span className="mx-2">»</span>
        <Link to="/articles" className="hover:text-ink-300">
          Журнал
        </Link>
        <span className="mx-2">»</span>
        <span className="text-ink-300 line-clamp-1">{article.title}</span>
      </div>

      <section className="relative w-full mt-2 min-h-[min(70vh,640px)] flex items-end overflow-hidden">
        {heroImage ? (
          <img
            src={heroImage}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-[center_25%]"
          />
        ) : (
          <div
            className="absolute inset-0"
            style={{ backgroundColor: theme.bg }}
          />
        )}
        <div
          className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/45 to-transparent"
          aria-hidden
        />

        <div className="relative z-10 w-full px-5 sm:px-10 lg:px-16 xl:px-20 pb-10 sm:pb-14 pt-28 text-white max-w-[1920px] mx-auto">
          {metaLine && (
            <p className="text-xs sm:text-sm uppercase tracking-[0.2em] text-white/70 mb-4">
              {metaLine}
            </p>
          )}
          <h1 className="font-serif text-3xl sm:text-5xl lg:text-6xl font-bold leading-[1.08] mb-4 max-w-4xl">
            {article.title}
          </h1>
          {director && (
            <p className="text-base sm:text-lg text-white/85 mb-2">
              О {director.title}
            </p>
          )}
          {article.author_name && (
            <p className="text-sm text-white/70">Автор: {article.author_name}</p>
          )}
        </div>
      </section>

      <article className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 py-12 sm:py-16 lg:py-20 max-w-3xl mx-auto">
        {article.summary && (
          <p className="text-lg sm:text-xl text-ink-300 leading-relaxed mb-10 font-medium">
            {article.summary}
          </p>
        )}

        <div className="max-w-none text-ink-500 space-y-6">
          {paragraphs.map((para, idx) => (
            <p key={idx} className="text-base sm:text-lg leading-[1.75]">
              {paragraphToNodes(para)}
            </p>
          ))}
        </div>

        {paragraphs.length === 0 && !article.summary && (
          <p className="text-ink-50">Текст статьи пока не добавлен.</p>
        )}

        {director && (
          <aside className="mt-14 pt-10 border-t border-ink-50/20">
            <Link
              to={`/director/${director.entity_id}`}
              className="text-sm text-wine-500 hover:underline"
            >
              Карточка режиссёра: {director.title}
            </Link>
          </aside>
        )}
      </article>

      <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 pb-16 sm:pb-24 max-w-[1920px] mx-auto flex flex-col sm:flex-row items-center justify-center gap-4">
        <Link
          to="/articles"
          className={cn(
            'inline-flex items-center justify-center px-8 py-4',
            'bg-ink-500 text-white text-sm sm:text-base font-medium uppercase tracking-wider',
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
      </div>
    </div>
  );
}
