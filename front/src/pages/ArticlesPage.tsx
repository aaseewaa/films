import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { listArticles } from '@/api/articles';
import { ArticleCard } from '@/components/articles/ArticleCard';
import { orderArticlesForJournal } from '@/lib/articleMosaic';

export function ArticlesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['articles', 'journal'],
    queryFn: () => listArticles({ lang: 'ru', limit: 20, offset: 0 }),
  });

  const articles = data ? orderArticlesForJournal(data.items) : [];

  return (
    <div className="bg-white min-h-[calc(100vh-4.75rem)] lg:min-h-[calc(100vh-5rem)]">
      <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 pt-8 sm:pt-10 pb-4 max-w-[1920px] mx-auto">
        <p className="text-xs uppercase tracking-[0.2em] text-ink-50 mb-1">
          Журнал
        </p>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-500">
          Статьи
        </h1>
      </div>

      <div className="w-full pb-16 max-w-[1920px] mx-auto">
        {isLoading && (
          <p className="text-center text-ink-50 py-24 px-6">Загружаем статьи…</p>
        )}

        {isError && (
          <p className="text-center text-wine-500 py-24 px-6">
            Не удалось загрузить статьи.
          </p>
        )}

        {!isLoading && !isError && articles.length === 0 && (
          <p className="text-center text-ink-50 py-24 px-6">
            Статей пока нет.
          </p>
        )}

        {!isLoading && !isError && articles.length > 0 && (
          <>
            {/* Мобила / планшет: вертикальные пары */}
            <div className="flex flex-col gap-1 px-2 sm:px-3 lg:hidden">
              {articles.map((article) => (
                <ArticleCard key={article.id} article={article} variant="stack" />
              ))}
            </div>

            {/* Десктоп: сетка 4 колонки как Another Gaze */}
            <div className="hidden lg:grid grid-cols-4 w-full gap-[3px] px-[3px] auto-rows-auto">
              {articles.map((article) => (
                <ArticleCard key={article.id} article={article} variant="grid" />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="w-full px-5 sm:px-10 pb-12 text-center">
        <Link
          to="/"
          className="text-sm text-ink-50 hover:text-wine-500 transition-colors"
        >
          ← На главную
        </Link>
      </div>
    </div>
  );
}
