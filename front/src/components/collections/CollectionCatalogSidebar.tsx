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
        'relative flex items-center h-11 w-full pl-4 pr-10 rounded-full border border-ink-50/20',
        'bg-white text-sm font-medium text-ink-400 cursor-pointer hover:border-ink-50/35',
      )}
    >
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent outline-none w-full cursor-pointer truncate"
        aria-label={label}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={16}
        className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-ink-50"
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
    <aside className={cn('flex flex-col gap-8', className)}>
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
        <h2 className="text-sm font-bold text-ink-500 uppercase tracking-wide mb-4">
          Быстрый поиск по темам
        </h2>
        <nav className="flex flex-col gap-0.5 max-h-[420px] overflow-y-auto pr-2">
          {COLLECTION_TOPICS.map((topic: CollectionTopic) => (
            <button
              key={topic.id}
              type="button"
              onClick={() => onTopicChange(topic.id)}
              className={cn(
                'text-left text-base py-2.5 px-1 transition-colors',
                topicId === topic.id
                  ? 'font-bold text-ink-500'
                  : 'text-ink-50 hover:text-ink-300',
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
