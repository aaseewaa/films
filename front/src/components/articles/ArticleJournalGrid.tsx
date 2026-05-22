import type { ArticleSummary } from '@/api/types';
import { ArticleCard } from '@/components/articles/ArticleCard';
import { cn } from '@/lib/utils';

interface ArticleJournalGridProps {
  articles: ArticleSummary[];
}

/** 50% | 25% | 25% */
const ROW_WIDE_LEFT = 'lg:grid-cols-[2fr_1fr_1fr]';
/** 25% | 25% | 50% */
const ROW_WIDE_RIGHT = 'lg:grid-cols-[1fr_1fr_2fr]';

/** Высота рядов 1–2 (+~12% к базе 52vw/620) */
const ROW_TALL_MIN_H = 'lg:min-h-[min(58vw,700px)]';
/** Ряд 3: на 20% ниже tall */
const ROW_SHORT_MIN_H = 'lg:min-h-[min(46.4vw,560px)]';

function buildJournalRows(items: ArticleSummary[]): ArticleSummary[][] {
  const rows: ArticleSummary[][] = [];
  let i = 0;

  const pattern = [3, 3, 4] as const;
  let patternIdx = 0;

  while (i < items.length) {
    const size = pattern[patternIdx % pattern.length];
    rows.push(items.slice(i, i + size));
    i += size;
    patternIdx += 1;
  }

  return rows;
}

/** Ряд 1: широкая слева, две узкие справа */
function WideLeftRow({ items }: { items: ArticleSummary[] }) {
  const [wide, narrowA, narrowB] = items;

  return (
    <div
      className={cn(
        'grid grid-cols-1 sm:grid-cols-2 gap-[3px] items-stretch',
        ROW_WIDE_LEFT,
        ROW_TALL_MIN_H,
      )}
    >
      {[
        { article: wide, split: '75-25' as const, className: 'sm:col-span-2 lg:col-span-1' },
        { article: narrowA, split: '45-55' as const },
        { article: narrowB, split: '45-55' as const },
      ].map(
        ({ article, split, className }, i) =>
          article && (
            <ArticleCard
              key={article.id}
              article={article}
              split={split}
              className={className}
            />
          ),
      )}
    </div>
  );
}

/** Ряд 2: две узкие слева, широкая справа */
function WideRightRow({ items }: { items: ArticleSummary[] }) {
  const [narrowA, narrowB, wide] = items;

  return (
    <div
      className={cn(
        'grid grid-cols-1 sm:grid-cols-2 gap-[3px] items-stretch',
        ROW_WIDE_RIGHT,
        ROW_TALL_MIN_H,
      )}
    >
      {[
        { article: narrowA, split: '45-55' as const },
        { article: narrowB, split: '45-55' as const },
        {
          article: wide,
          split: '75-25' as const,
          className: 'sm:col-span-2 lg:col-span-1',
        },
      ].map(
        ({ article, split, className }) =>
          article && (
            <ArticleCard
              key={article.id}
              article={article}
              split={split}
              className={className}
            />
          ),
      )}
    </div>
  );
}

/** Ряд 3: 4 равные колонки, фото 60% / текст 40% (текст внизу), ниже рядов 1–2 на 20% */
function QuartetRow({ items }: { items: ArticleSummary[] }) {
  return (
    <div
      className={cn(
        'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[3px] items-stretch',
        ROW_SHORT_MIN_H,
      )}
    >
      {items.map((article) => (
        <ArticleCard key={article.id} article={article} split="60-40" />
      ))}
    </div>
  );
}

export function ArticleJournalGrid({ articles }: ArticleJournalGridProps) {
  const rows = buildJournalRows(articles);

  return (
    <div className="flex flex-col gap-[3px] px-[3px]">
      {rows.map((row, rowIndex) => {
        const layout = rowIndex % 3;
        if (layout === 0) {
          return <WideLeftRow key={rowIndex} items={row} />;
        }
        if (layout === 1) {
          return <WideRightRow key={rowIndex} items={row} />;
        }
        return <QuartetRow key={rowIndex} items={row} />;
      })}
    </div>
  );
}
