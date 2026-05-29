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
          large ? 'h-14 sm:h-[3.75rem] pl-5 sm:pl-6 pr-11 text-lg sm:text-xl' : 'h-12 sm:h-14 pl-4 sm:pl-5 pr-10 text-base sm:text-lg',
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
            'appearance-none bg-transparent text-inherit outline-none cursor-pointer pr-1 truncate disabled:cursor-not-allowed',
            large ? 'min-w-[10rem] sm:min-w-[12rem] max-w-[16rem] sm:max-w-[18rem]' : 'min-w-[8rem] sm:min-w-[9rem] max-w-[13rem] sm:max-w-[15rem]',
          )}
          aria-label={label}
        >
          {children}
        </select>
        <ChevronDown
          size={large ? 22 : 18}
          className="catalog-pill-icon absolute right-3.5 sm:right-4 top-1/2 -translate-y-1/2 pointer-events-none transition-colors"
        />
    </label>
  );
}

function TabPill({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'catalog-pill catalog-pluffy-tab inline-flex items-center h-14 sm:h-16 px-7 sm:px-10 rounded-full',
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
}: FilmCatalogFiltersProps) {
  const yearValue =
    YEAR_OPTIONS.find(
      (o) => o.from === filters.yearFrom && o.to === filters.yearTo,
    )?.label ?? 'Все годы';

  return (
    <div className="space-y-5 sm:space-y-6">
      <div className="flex flex-wrap items-center gap-3 sm:gap-4 lg:gap-5">
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          <TabPill
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
            active={filters.catalogType === 'animation'}
            onClick={() => {
              if (filters.catalogType !== 'animation') {
                onChange({ ...filters, catalogType: 'animation', genre: undefined });
              }
            }}
          >
            Мультфильмы
          </TabPill>
        </div>

        <span className="hidden sm:block w-px h-12 sm:h-14 bg-ink-50/20 mx-0.5 self-center" aria-hidden />

        <FilterSelect
          label="Год"
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
          size="large"
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
          className="text-base sm:text-lg text-ink-50 transition-colors hover:text-[#0abab5]"
        >
          ✕ Сбросить фильтры
        </button>
      )}
    </div>
  );
}
