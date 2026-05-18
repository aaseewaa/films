import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listCollections } from '@/api/collections';
import type { CollectionSummary } from '@/api/types';
import { CollectionCatalogCard } from '@/components/collections/CollectionCatalogCard';
import { CollectionCatalogSidebar } from '@/components/collections/CollectionCatalogSidebar';
import {
  COLLECTION_TOPICS,
  type CollectionSort,
} from '@/lib/collectionTopics';

function filterAndSort(
  items: CollectionSummary[],
  topicId: string,
  sort: CollectionSort,
): CollectionSummary[] {
  let list = [...items];

  if (topicId !== 'all' && topicId !== 'featured') {
    list = list.filter((c) => c.tags.includes(topicId));
  }

  switch (sort) {
    case 'title':
      list.sort((a, b) => a.title.localeCompare(b.title, 'ru'));
      break;
    case 'films_desc':
      list.sort((a, b) => b.items_count - a.items_count);
      break;
    case 'popular':
    default:
      list.sort((a, b) => {
        if (a.is_featured !== b.is_featured) return a.is_featured ? -1 : 1;
        return b.items_count - a.items_count;
      });
  }

  return list;
}

export function CollectionsPage() {
  const [topicId, setTopicId] = useState('all');
  const [sort, setSort] = useState<CollectionSort>('popular');

  const topic = COLLECTION_TOPICS.find((t) => t.id === topicId);
  const featuredOnly = topic?.featuredOnly ?? false;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['collections', 'editorial', featuredOnly],
    queryFn: () =>
      listCollections({
        kind: 'editorial',
        lang: 'ru',
        only_featured: featuredOnly,
        limit: 50,
      }),
  });

  const collections = useMemo(() => {
    if (!data?.items) return [];
    return filterAndSort(data.items, topicId, sort);
  }, [data?.items, topicId, sort]);

  return (
    <div className="bg-white min-h-[calc(100vh-4.75rem)] lg:min-h-[calc(100vh-5rem)]">
      <div className="max-w-page w-full mx-auto px-4 sm:px-8 lg:px-12 xl:px-16 py-8 sm:py-12">
        <header className="mb-8 lg:mb-10">
          <h1 className="text-2xl sm:text-3xl font-bold text-ink-500 uppercase tracking-wide">
            Коллекции
          </h1>
        </header>

        <div className="lg:hidden mb-8">
          <CollectionCatalogSidebar
            topicId={topicId}
            sort={sort}
            onTopicChange={setTopicId}
            onSortChange={setSort}
          />
        </div>

        <div className="flex gap-10 xl:gap-16">
          <CollectionCatalogSidebar
            className="hidden lg:flex w-[220px] xl:w-[260px] shrink-0"
            topicId={topicId}
            sort={sort}
            onTopicChange={setTopicId}
            onSortChange={setSort}
          />

          <section className="flex-1 min-w-0">
            {isLoading && (
              <p className="text-ink-50 py-16 text-center">Загружаем коллекции…</p>
            )}

            {isError && (
              <p className="text-wine-500 py-16 text-center">
                Не удалось загрузить коллекции. Запущен ли бэкенд?
              </p>
            )}

            {!isLoading && !isError && collections.length === 0 && (
              <p className="text-ink-50 py-16 text-center">
                По выбранной теме коллекций нет.
              </p>
            )}

            {collections.map((c) => (
              <CollectionCatalogCard key={c.id} collection={c} />
            ))}
          </section>
        </div>
      </div>
    </div>
  );
}
