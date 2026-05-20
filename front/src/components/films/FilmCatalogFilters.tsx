import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FilmSortBy, GenreItem } from '@/api/types';

export interface FilmFiltersState {
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
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        'relative inline-flex items-center h-10 pl-4 pr-9 rounded-full border border-ink-50/20',
        'bg-white text-sm font-medium text-ink-400',
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-ink-50/35',
      )}
    >
      <span className="sr-only">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent outline-none cursor-pointer pr-1 min-w-[7rem] max-w-[11rem] truncate disabled:cursor-not-allowed"
        aria-label={label}
      >
        {children}
      </select>
      <ChevronDown
        size={16}
        className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-ink-50"
      />
    </label>
  );
}

function TabPill({
  active,
  disabled,
  children,
}: {
  active?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center h-10 px-5 rounded-full text-sm font-semibold uppercase tracking-wide',
        active && 'bg-ink-500 text-white',
        !active && !disabled && 'bg-white border border-ink-50/20 text-ink-400',
        disabled && 'bg-white/60 border border-ink-50/10 text-ink-50',
      )}
    >
      {children}
    </span>
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <TabPill active>Фильмы</TabPill>
        <TabPill disabled>Сериалы</TabPill>

        <span className="hidden sm:block w-px h-6 bg-ink-50/20 mx-1" aria-hidden />

        <FilterSelect
          label="Год"
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
          className="text-sm text-ink-50 hover:text-ink-300 transition-colors"
        >
          ✕ Сбросить фильтры
        </button>
      )}
    </div>
  );
}
