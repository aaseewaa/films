import type { ArticleSummary } from '@/api/types';
import { ArticleCard } from '@/components/articles/ArticleCard';

interface ArticleJournalGridProps {
  articles: ArticleSummary[];
}

type JournalRowKind = 'featured-left' | 'featured-right' | 'quarters';

/** Повторяемый цикл: 3 + 3 + 4, как в макете anothergaze */
const ROW_PATTERN: { count: number; kind: JournalRowKind }[] = [
  { count: 3, kind: 'featured-left' },
  { count: 3, kind: 'featured-right' },
  { count: 4, kind: 'quarters' },
];

function buildJournalRows(articles: ArticleSummary[]) {
  const rows: { kind: JournalRowKind; items: ArticleSummary[] }[] = [];
  let i = 0;
  let patternIdx = 0;

  while (i < articles.length) {
    const { count, kind } = ROW_PATTERN[patternIdx % ROW_PATTERN.length];
    const items = articles.slice(i, i + count);
    if (items.length > 0) {
      rows.push({ kind, items });
    }
    i += count;
    patternIdx += 1;
  }

  return rows;
}

/** Сетка журнала: чередование крупных рядов (3) и ряда из четырёх карточек */
export function ArticleJournalGrid({ articles }: ArticleJournalGridProps) {
  const rows = buildJournalRows(articles);

  return (
    <div className="flex flex-col gap-[3px] px-[3px]">
      {rows.map((row, idx) => {
        if (row.kind === 'featured-left') {
          return <FeaturedLeftRow key={idx} items={row.items} />;
        }
        if (row.kind === 'featured-right') {
          return <FeaturedRightRow key={idx} items={row.items} />;
        }
        return <QuartersRow key={idx} items={row.items} />;
      })}
    </div>
  );
}

function FeaturedLeftRow({ items }: { items: ArticleSummary[] }) {
  const [featured, ...stacked] = items;

  return (
    <JournalRow>
      {featured && (
        <ArticleCard article={featured} layout="featured" className="lg:col-span-2" />
      )}
      {stacked.length > 0 && (
        <StackColumn>
          {stacked.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              layout="half"
              className="flex-1 min-h-0"
            />
          ))}
        </StackColumn>
      )}
    </JournalRow>
  );
}

function FeaturedRightRow({ items }: { items: ArticleSummary[] }) {
  const featured = items[items.length - 1];
  const stacked = items.slice(0, -1);

  return (
    <JournalRow>
      {stacked.length > 0 && (
        <StackColumn className="order-2 lg:order-1">
          {stacked.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              layout="half"
              className="flex-1 min-h-0"
            />
          ))}
        </StackColumn>
      )}
      {featured && (
        <ArticleCard
          article={featured}
          layout="featured"
          className="lg:col-span-2 order-1 lg:order-2"
        />
      )}
    </JournalRow>
  );
}

function QuartersRow({ items }: { items: ArticleSummary[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[3px]">
      {items.map((article) => (
        <ArticleCard key={article.id} article={article} layout="quarter" />
      ))}
    </div>
  );
}

function StackColumn({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-[3px] lg:col-span-1 min-h-0 ${className}`.trim()}>
      {children}
    </div>
  );
}

function JournalRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-[3px] lg:items-stretch lg:min-h-[480px]">
      {children}
    </div>
  );
}
