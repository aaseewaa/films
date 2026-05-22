import { ChevronDown } from 'lucide-react';
import {
  COLLECTION_SORT_OPTIONS,
  COLLECTION_TOPICS,
  type CollectionSort,
  type CollectionTopic,
} from '@/lib/collectionTopics';
import { cn } from '@/lib/utils';

interface CollectionCatalogSidebarProps {
  topicId: string;
  sort: CollectionSort;
  onTopicChange: (id: string) => void;
  onSortChange: (sort: CollectionSort) => void;
  className?: string;
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label
      className={cn(
        'group relative flex items-center h-14 sm:h-[3.75rem] w-full pl-6 pr-12 rounded-full border border-ink-50/20',
        'bg-site-bg text-lg sm:text-xl font-medium text-ink-400 cursor-pointer transition-colors duration-150',
        'hover:border-tiffany hover:bg-[rgba(10,186,181,0.16)]',
        'focus-within:border-tiffany focus-within:bg-[rgba(10,186,181,0.24)]',
        'active:border-tiffany active:bg-[rgba(10,186,181,0.24)]',
      )}
    >
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent outline-none w-full cursor-pointer truncate text-inherit"
        aria-label={label}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={22}
        className={cn(
          'absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-ink-50 transition-colors',
          'group-hover:text-tiffany group-focus-within:text-tiffany',
        )}
      />
    </label>
  );
}

export function CollectionCatalogSidebar({
  topicId,
  sort,
  onTopicChange,
  onSortChange,
  className,
}: CollectionCatalogSidebarProps) {
  return (
    <aside className={cn('flex flex-col gap-10', className)}>
      <div className="space-y-3">
        <FilterSelect
          label="Сортировка"
          value={sort}
          onChange={(v) => onSortChange(v as CollectionSort)}
          options={COLLECTION_SORT_OPTIONS.map((o) => ({
            value: o.value,
            label: o.label,
          }))}
        />
      </div>

      <div>
        <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-ink-500 uppercase tracking-wide mb-6 pl-2">
          Быстрый поиск по темам
        </h2>
        <nav className="flex flex-col gap-1.5 max-h-[520px] overflow-y-auto pr-2 pl-5 sm:pl-7">
          {COLLECTION_TOPICS.map((topic: CollectionTopic) => (
            <button
              key={topic.id}
              type="button"
              onClick={() => onTopicChange(topic.id)}
              className={cn(
                'text-left text-xl sm:text-2xl py-3.5 pr-2 transition-colors leading-snug',
                topicId === topic.id
                  ? 'font-bold text-tiffany'
                  : 'text-ink-50 hover:text-tiffany',
              )}
            >
              {topic.label}
            </button>
          ))}
        </nav>
      </div>
    </aside>
  );
}
