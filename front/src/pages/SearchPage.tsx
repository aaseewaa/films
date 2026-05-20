import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { searchEntities } from '@/api/search';
import type { SearchMode } from '@/api/types';
import { SearchHitCard } from '@/components/search/SearchHitCard';
import { cn } from '@/lib/utils';

type EntityFilter = 'all' | 'film' | 'person';

function parseMode(value: string | null): SearchMode {
  return value === 'semantic' ? 'semantic' : 'hybrid';
}

function parseType(value: string | null): EntityFilter {
  if (value === 'film' || value === 'person') return value;
  return 'all';
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const qParam = searchParams.get('q')?.trim() ?? '';
  const mode = parseMode(searchParams.get('mode'));
  const typeFilter = parseType(searchParams.get('type'));

  const [input, setInput] = useState(qParam);

  useEffect(() => {
    setInput(qParam);
  }, [qParam]);

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['search', qParam, mode, typeFilter],
    queryFn: () =>
      searchEntities({
        q: qParam,
        mode,
        lang: 'ru',
        type: typeFilter === 'all' ? undefined : typeFilter,
        limit: 30,
      }),
    enabled: qParam.length >= 1,
    retry: 1,
  });

  function applySearch(next: {
    q?: string;
    mode?: SearchMode;
    type?: EntityFilter;
  }) {
    const q = (next.q ?? (qParam || input)).trim();
    const nextMode = next.mode ?? mode;
    const nextType = next.type ?? typeFilter;

    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (nextMode === 'semantic') params.set('mode', 'semantic');
    if (nextType !== 'all') params.set('type', nextType);
    setSearchParams(params, { replace: true });
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    applySearch({ q: input });
  }

  const strategies =
    data?.used_strategies?.length ? data.used_strategies.join(', ') : null;

  return (
    <div className="bg-white min-h-[calc(100vh-4.75rem)] lg:min-h-[calc(100vh-5rem)]">
      <div className="w-full max-w-4xl mx-auto px-5 sm:px-10 lg:px-16 py-8 sm:py-12">
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-500 mb-6">
          Поиск
        </h1>

        <form onSubmit={onSubmit} className="mb-6">
          <div className="relative">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-50 pointer-events-none"
              size={20}
              strokeWidth={1.75}
            />
            <input
              type="search"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Фильмы, режиссёры, сюжет…"
              className={cn(
                'w-full h-12 sm:h-14 pl-12 pr-4 text-base sm:text-lg',
                'border border-ink-50/20 rounded-sm bg-cream-50',
                'text-ink-500 placeholder:text-ink-50',
                'focus:outline-none focus:border-wine-500',
              )}
              autoFocus
            />
          </div>
        </form>

        <div className="flex flex-wrap gap-2 sm:gap-3 mb-8">
          <FilterChip
            active={mode === 'hybrid'}
            onClick={() => applySearch({ mode: 'hybrid' })}
          >
            По названию
          </FilterChip>
          <FilterChip
            active={mode === 'semantic'}
            onClick={() => applySearch({ mode: 'semantic' })}
          >
            По смыслу
          </FilterChip>

          <span className="w-px h-8 bg-ink-50/20 hidden sm:block self-center mx-1" />

          {(['all', 'film', 'person'] as const).map((t) => (
            <FilterChip
              key={t}
              active={typeFilter === t}
              onClick={() => applySearch({ type: t })}
              variant="muted"
            >
              {t === 'all' ? 'Все' : t === 'film' ? 'Фильмы' : 'Люди'}
            </FilterChip>
          ))}
        </div>

        {!qParam && (
          <p className="text-ink-100 text-base">
            Введите запрос. Режим «По смыслу» ищет по описаниям через эмбеддинги
            (pgvector), «По названию» — по тексту и опечаткам.
          </p>
        )}

        {qParam && isLoading && (
          <p className="text-ink-50">Ищем…</p>
        )}

        {qParam && isError && (
          <p className="text-wine-600">
            Не удалось выполнить поиск. Проверьте, что API запущен
            {mode === 'semantic' && ' и установлен sentence-transformers'}.
          </p>
        )}

        {qParam && data && !isLoading && (
          <>
            <p className="text-sm text-ink-50 mb-6">
              {data.total === 0
                ? 'Ничего не найдено'
                : `Найдено: ${data.total}`}
              {data.detected_language && data.total > 0 && (
                <> · язык: {data.detected_language}</>
              )}
              {strategies && mode === 'hybrid' && (
                <> · {strategies}</>
              )}
              {isFetching && !isLoading && ' · обновляем…'}
            </p>

            {data.items.length > 0 ? (
              <div className="border-t border-ink-50/15">
                {data.items.map((hit) => (
                  <SearchHitCard key={`${hit.entity_type}-${hit.entity_id}`} hit={hit} />
                ))}
              </div>
            ) : (
              <p className="text-ink-100">
                Попробуйте другой запрос
                {mode === 'hybrid' ? ' или режим «По смыслу»' : ' или «По названию»'}.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function FilterChip({
  children,
  active,
  onClick,
  variant = 'default',
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
  variant?: 'default' | 'muted';
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'px-3 sm:px-4 py-2 text-xs sm:text-sm uppercase tracking-[0.08em] font-semibold',
        'border rounded-sm transition-colors',
        active
          ? 'bg-ink-500 text-white border-ink-500'
          : variant === 'muted'
            ? 'bg-transparent text-ink-300 border-ink-50/25 hover:border-ink-50/40'
            : 'bg-cream-100 text-ink-400 border-ink-50/20 hover:border-ink-50/35',
      )}
    >
      {children}
    </button>
  );
}
