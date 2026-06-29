import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FilmCatalogType } from '@/api/catalog';
import type { FilmSortBy, GenreItem } from '@/api/types';

export type { FilmCatalogType };

export interface FilmFiltersState {
  catalogType: FilmCatalogType;
  yearFrom?: number;
  yearTo?: number;
  genre?: string;
  country?: string;
  sortBy: FilmSortBy;
}

interface FilmCatalogFiltersProps {
  filters: FilmFiltersState;
  genres: GenreItem[];
  countries: GenreItem[];
  onChange: (next: FilmFiltersState) => void;
  onReset: () => void;
  hasActiveFilters: boolean;
  size?: 'default' | 'large';
}

const YEAR_OPTIONS: { label: string; from?: number; to?: number }[] = [
  { label: 'Все годы' },
  { label: '2020–2029', from: 2020, to: 2029 },
  { label: '2010–2019', from: 2010, to: 2019 },
  { label: '2000–2009', from: 2000, to: 2009 },
  { label: '1990–1999', from: 1990, to: 1999 },
  { label: '1980–1989', from: 1980, to: 1989 },
  { label: '1970–1979', from: 1970, to: 1979 },
  { label: 'до 1970', from: 1880, to: 1969 },
];

const SORT_OPTIONS: { value: FilmSortBy; label: string }[] = [
  { value: 'popularity', label: 'По популярности' },
  { value: 'vote_average', label: 'По рейтингу' },
  { value: 'year', label: 'Сначала новые' },
  { value: 'year_asc', label: 'Сначала старые' },
  { value: 'title', label: 'По алфавиту' },
];

function FilterSelect({
  label,
  value,
  onChange,
  children,
  disabled,
  active,
  size = 'default',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
  disabled?: boolean;
  active?: boolean;
  size?: 'default' | 'large';
}) {
  const large = size === 'large';

  return (
    <label
        className={cn(
          'catalog-pill group relative inline-flex items-center rounded-full font-medium',
          large
            ? 'h-[3.75rem] sm:h-[4.125rem] flex-1 min-w-[8rem] basis-0 pl-4 sm:pl-5 pr-9 sm:pr-10 text-[1.3125rem] sm:text-2xl'
            : 'h-10 sm:h-11 shrink-0 pl-3.5 sm:pl-4 pr-9 text-sm sm:text-base',
          disabled && 'opacity-50 cursor-not-allowed pointer-events-none',
          !disabled && active && 'is-active',
          !disabled && 'cursor-pointer',
        )}
    >
      <span className="sr-only">{label}</span>
        <select
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            'appearance-none bg-transparent text-inherit outline-none cursor-pointer w-full min-w-0 disabled:cursor-not-allowed',
            large ? 'pr-1' : 'truncate min-w-[8rem] sm:min-w-[9rem] max-w-[13rem] sm:max-w-[15rem] pr-1',
          )}
          aria-label={label}
        >
          {children}
        </select>
        <ChevronDown
          size={large ? 22 : 18}
          className={cn(
            'catalog-pill-icon absolute top-1/2 -translate-y-1/2 pointer-events-none transition-colors',
            large ? 'right-3.5 sm:right-4' : 'right-3.5 sm:right-4',
          )}
        />
    </label>
  );
}

function TabPill({
  active,
  onClick,
  children,
  large,
}: {
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  large?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'catalog-pill catalog-pluffy-tab inline-flex items-center rounded-full shrink-0 whitespace-nowrap',
        large ? 'h-[4.125rem] sm:h-[4.5rem] px-4 sm:px-6' : 'h-11 sm:h-12 px-5 sm:px-7',
        active && 'is-active',
      )}
    >
      {children}
    </button>
  );
}

export function FilmCatalogFilters({
  filters,
  genres,
  countries,
  onChange,
  onReset,
  hasActiveFilters,
  size = 'default',
}: FilmCatalogFiltersProps) {
  const large = size === 'large';
  const yearValue =
    YEAR_OPTIONS.find(
      (o) => o.from === filters.yearFrom && o.to === filters.yearTo,
    )?.label ?? 'Все годы';

  return (
    <div className={cn(large ? 'space-y-8 sm:space-y-10' : 'space-y-5 sm:space-y-6')}>
      <div
        className={cn(
          large ? 'films-catalog-filters-row' : 'flex flex-wrap items-center gap-3 sm:gap-4 lg:gap-5',
        )}
      >
          <TabPill
            large={large}
            active={filters.catalogType === 'films'}
            onClick={() => {
              if (filters.catalogType !== 'films') {
                onChange({ ...filters, catalogType: 'films' });
              }
            }}
          >
            Все фильмы
          </TabPill>
          <TabPill
            large={large}
            active={filters.catalogType === 'animation'}
            onClick={() => {
              if (filters.catalogType !== 'animation') {
                onChange({ ...filters, catalogType: 'animation', genre: undefined });
              }
            }}
          >
            Мультфильмы
          </TabPill>

        <span
          className={cn(
            'hidden sm:block w-px bg-ink-50/20 self-center shrink-0',
            large ? 'h-[4.5rem] sm:h-[5.25rem]' : 'h-12 sm:h-14 mx-0.5',
          )}
          aria-hidden
        />

        <FilterSelect
          label="Год"
          size={size}
          active={filters.yearFrom != null || filters.yearTo != null}
          value={yearValue}
          onChange={(label) => {
            const opt = YEAR_OPTIONS.find((o) => o.label === label);
            onChange({
              ...filters,
              yearFrom: opt?.from,
              yearTo: opt?.to,
            });
          }}
        >
          {YEAR_OPTIONS.map((o) => (
            <option key={o.label} value={o.label}>
              {o.label}
            </option>
          ))}
        </FilterSelect>

        <FilterSelect
          label="Жанр"
          size={size}
          active={!!filters.genre}
          value={filters.genre ?? ''}
          onChange={(code) => {
            onChange({ ...filters, genre: code || undefined });
          }}
        >
          <option value="">Все жанры</option>
          {genres.map((g) => (
            <option key={g.id} value={g.code ?? ''}>
              {g.name} ({g.films_count})
            </option>
          ))}
        </FilterSelect>

        <FilterSelect
          label="Производство"
          size={size}
          active={!!filters.country}
          value={filters.country ?? ''}
          disabled={countries.length === 0}
          onChange={(code) => {
            onChange({ ...filters, country: code || undefined });
          }}
        >
          <option value="">
            {countries.length === 0 ? 'Нет данных' : 'Производство'}
          </option>
          {countries.map((c) => (
            <option key={c.code ?? c.id} value={c.code ?? ''}>
              {c.name} ({c.films_count})
            </option>
          ))}
        </FilterSelect>

        <FilterSelect
          label="Сортировка"
          size={size}
          active={filters.sortBy !== 'popularity'}
          value={filters.sortBy}
          onChange={(sortBy) => {
            onChange({ ...filters, sortBy: sortBy as FilmSortBy });
          }}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </FilterSelect>
      </div>

      {hasActiveFilters && (
        <button
          type="button"
          onClick={onReset}
          className={cn(
            'text-ink-50 transition-colors hover:text-[#0abab5]',
            large ? 'text-[1.5rem] sm:text-[1.6875rem]' : 'text-base sm:text-lg',
          )}
        >
          ✕ Сбросить фильтры
        </button>
      )}
    </div>
  );
}
