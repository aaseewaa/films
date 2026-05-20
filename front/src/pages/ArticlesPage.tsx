import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listArticles } from '@/api/articles';
import { ArticleJournalGrid } from '@/components/articles/ArticleJournalGrid';
import { ArticleCard } from '@/components/articles/ArticleCard';
import { orderArticlesForJournal } from '@/lib/articleMosaic';

export function ArticlesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['articles', 'journal'],
    queryFn: () => listArticles({ lang: 'ru', limit: 50, offset: 0 }),
    retry: 1,
  });

  const articles = useMemo(
    () => orderArticlesForJournal(data?.items ?? []),
    [data],
  );

  return (
    <div className="bg-white min-h-[calc(100vh-4.75rem)] lg:min-h-[calc(100vh-5rem)]">
      <div className="w-full pb-16 max-w-[1920px] mx-auto">
        {isLoading && (
          <p className="text-center text-ink-50 text-sm py-12 px-6">
            Загружаем статьи…
          </p>
        )}

        {isError && (
          <p className="text-center text-ink-50 text-sm py-4 px-6">
            Не удалось загрузить журнал. Проверьте, что бэкенд запущен.
          </p>
        )}

        {!isLoading && !isError && articles.length === 0 && (
          <p className="text-center text-ink-50 text-sm py-12 px-6">
            Пока нет опубликованных статей.
          </p>
        )}

        {articles.length > 0 && (
          <>
            <div className="flex flex-col gap-[3px] px-[3px] lg:hidden">
              {articles.map((article) => (
                <ArticleCard key={article.id} article={article} layout="quarter" />
              ))}
            </div>

            <div className="hidden lg:block">
              <ArticleJournalGrid articles={articles} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
