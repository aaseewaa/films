import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listArticles } from '@/api/articles';
import { useSiteLang } from '@/lib/siteLang';
import { ArticleJournalGrid } from '@/components/articles/ArticleJournalGrid';
import { PageContent } from '@/components/layout/PageContent';
import { orderArticlesForJournal } from '@/lib/articleMosaic';

export function ArticlesPage() {
  const lang = useSiteLang();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['articles', 'journal', lang],
    queryFn: () => listArticles({ limit: 50, offset: 0 }),
    retry: 1,
  });

  const articles = useMemo(
    () => orderArticlesForJournal(data?.items ?? []),
    [data],
  );

  return (
    <div className="bg-site-bg min-h-[calc(100vh-5.75rem)] sm:min-h-[calc(100vh-6rem)] lg:min-h-[calc(100vh-6.5rem)]">
      <PageContent className="pb-16">
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

        {articles.length > 0 && <ArticleJournalGrid articles={articles} />}
      </PageContent>
    </div>
  );
}
