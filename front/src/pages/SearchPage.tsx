import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { searchEntities } from '@/api/search';
import type { SearchMode } from '@/api/types';
import { SearchHitCard } from '@/components/search/SearchHitCard';
import { PageContent } from '@/components/layout/PageContent';
import { useTranslation } from '@/hooks/useTranslation';
import { useSiteLang } from '@/lib/siteLang';
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
  const lang = useSiteLang();
  const tr = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const qParam = searchParams.get('q')?.trim() ?? '';
  const mode = parseMode(searchParams.get('mode'));
  const typeFilter = parseType(searchParams.get('type'));

  const [input, setInput] = useState(qParam);

  useEffect(() => {
    setInput(qParam);
  }, [qParam]);

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['search', qParam, mode, typeFilter, lang],
    queryFn: () =>
      searchEntities({
        q: qParam,
        mode,
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
    <div className="bg-site-bg min-h-[calc(100vh-5.75rem)] sm:min-h-[calc(100vh-6rem)] lg:min-h-[calc(100vh-6.5rem)]">
      <PageContent className="pt-16 sm:pt-20 lg:pt-24 pb-8 sm:pb-12">
        <section className="flex flex-col items-center text-center">
          <h1 className="catalog-pluffy-title mb-6 sm:mb-8">{tr('searchTitle')}</h1>

          <form onSubmit={onSubmit} className="mb-8 sm:mb-10 w-full flex justify-center">
            <div className="relative w-full max-w-[min(72%,52rem)]">
              <Search
                className="absolute left-5 sm:left-6 top-1/2 -translate-y-1/2 text-ink-50 pointer-events-none"
                size={22}
                strokeWidth={1.75}
              />
              <input
                type="search"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={tr('searchPlaceholder')}
                className={cn(
                  'w-full h-14 sm:h-16 pl-14 sm:pl-16 pr-5',
                'font-sans text-lg sm:text-xl text-ink-500',
                'border-2 border-ink-50/25 rounded-2xl bg-site-bg',
                'placeholder:font-pluffy-outline placeholder:uppercase placeholder:tracking-wide',
                'placeholder:text-[1.35rem] sm:placeholder:text-[1.65rem] placeholder:font-normal',
                'placeholder:text-[#0ABAB5] placeholder:opacity-90',
                'hover:bg-site-bg focus:bg-site-bg',
                'focus:outline-none focus:border-[#0ABAB5] transition-colors',
              )}
                autoFocus
              />
            </div>
          </form>

          <div className="flex flex-nowrap items-center justify-center gap-3 sm:gap-4 mb-8 sm:mb-10 max-w-full overflow-x-auto pb-1">
          <FilterChip
            active={mode === 'hybrid'}
            onClick={() => applySearch({ mode: 'hybrid' })}
          >
            {tr('searchByTitle')}
          </FilterChip>
          <FilterChip
            active={mode === 'semantic'}
            onClick={() => applySearch({ mode: 'semantic' })}
          >
            {tr('searchByMeaning')}
          </FilterChip>

          <span className="w-px h-10 sm:h-12 bg-ink-50/20 shrink-0 self-center mx-0.5 sm:mx-1" />

          {(['all', 'film', 'person'] as const).map((t) => (
            <FilterChip
              key={t}
              active={typeFilter === t}
              onClick={() => applySearch({ type: t })}
              variant="muted"
            >
              {t === 'all' ? tr('searchAll') : t === 'film' ? tr('searchFilms') : tr('searchPeople')}
            </FilterChip>
          ))}
          </div>
        </section>

        {!qParam && (
          <p className="text-ink-100 text-base">{tr('searchHint')}</p>
        )}

        {qParam && (
          <div className="search-results px-10 sm:px-14 md:px-20 lg:px-28 xl:px-36">
            {isLoading && <p className="text-ink-50">{tr('searchLoading')}</p>}

            {isError && (
              <p className="text-wine-600">{tr('searchError')}</p>
            )}

            {data && !isLoading && (
              <>
                <p className="text-base sm:text-lg text-ink-50 mb-8 sm:mb-10">
                  {data.total === 0
                    ? mode === 'semantic'
                      ? 'Нет близких совпадений по смыслу (порог 38%)'
                      : tr('searchEmpty')
                    : `${tr('searchFound')}: ${data.total}`}
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
                  <p className="text-ink-100">{tr('searchTryOther')}</p>
                )}
              </>
            )}
          </div>
        )}
      </PageContent>
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
        'shrink-0 px-5 sm:px-6 py-3 sm:py-3.5 text-sm sm:text-base uppercase tracking-[0.08em] font-semibold',
        'border rounded-sm transition-colors text-ink-500',
        active
          ? 'search-filter-chip-active'
          : variant === 'muted'
            ? 'bg-transparent text-ink-300 border-ink-50/25 hover:border-ink-50/40'
            : 'bg-site-bg text-ink-400 border-ink-50/20 hover:border-ink-50/35',
      )}
    >
      {children}
    </button>
  );
}
