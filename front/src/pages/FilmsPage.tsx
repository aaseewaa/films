import { useMemo, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { listFilms, listGenres, listProductionCountries } from '@/api/catalog';
import type { FilmSortBy } from '@/api/types';
import {
  FilmCatalogFilters,
  type FilmFiltersState,
} from '@/components/films/FilmCatalogFilters';
import { FilmCatalogCard } from '@/components/films/FilmCatalogCard';
import { Button } from '@/components/ui/Button';

const PAGE_SIZE = 20;

const DEFAULT_FILTERS: FilmFiltersState = {
  sortBy: 'vote_average',
};

function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

export function FilmsPage() {
  const [filters, setFilters] = useState<FilmFiltersState>(DEFAULT_FILTERS);

  const filterKey = useMemo(
    () =>
      JSON.stringify({
        genre: filters.genre,
        country: filters.country,
        yearFrom: filters.yearFrom,
        yearTo: filters.yearTo,
        sortBy: filters.sortBy,
      }),
    [filters],
  );

  const hasActiveFilters =
    !!filters.genre ||
    !!filters.country ||
    filters.yearFrom != null ||
    filters.yearTo != null ||
    filters.sortBy !== DEFAULT_FILTERS.sortBy;

  const { data: genres = [] } = useQuery({
    queryKey: ['genres', 'ru'],
    queryFn: () => listGenres('ru'),
  });

  const { data: countries = [] } = useQuery({
    queryKey: ['production-countries', 'ru'],
    queryFn: () => listProductionCountries('ru'),
  });

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['films', 'catalog', filterKey],
    queryFn: ({ pageParam }) =>
      listFilms({
        lang: 'ru',
        genre: filters.genre,
        country: filters.country,
        year_from: filters.yearFrom,
        year_to: filters.yearTo,
        sort_by: filters.sortBy,
        limit: PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.limit;
      return next < last.total ? next : undefined;
    },
  });

  const films = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  return (
    <div className="bg-white min-h-[calc(100vh-4.75rem)] lg:min-h-[calc(100vh-5rem)]">
      <div className="max-w-page w-full mx-auto px-4 sm:px-8 lg:px-12 xl:px-16 py-8 sm:py-12">
        <header className="mb-8 sm:mb-10">
          <h1 className="text-2xl sm:text-3xl font-bold text-ink-500 uppercase tracking-wide mb-2">
            Все фильмы
          </h1>
          <p className="text-base text-ink-50">
            {isLoading
              ? 'Загружаем каталог…'
              : `${total.toLocaleString('ru-RU')} ${pluralFilms(total)} в коллекции`}
          </p>
        </header>

        <FilmCatalogFilters
          filters={filters}
          genres={genres}
          countries={countries}
          onChange={setFilters}
          onReset={() => setFilters(DEFAULT_FILTERS)}
          hasActiveFilters={hasActiveFilters}
        />

        <section className="mt-10 sm:mt-12">
          {isLoading && (
            <p className="text-ink-50 py-16 text-center">Загрузка фильмов…</p>
          )}

          {isError && (
            <p className="text-wine-500 py-16 text-center">
              Не удалось загрузить каталог. Проверьте, что бэкенд запущен.
            </p>
          )}

          {!isLoading && !isError && films.length === 0 && (
            <p className="text-ink-50 py-16 text-center">
              По выбранным фильтрам ничего не найдено.
            </p>
          )}

          {films.map((film) => (
            <FilmCatalogCard key={film.id} film={film} />
          ))}

          {hasNextPage && (
            <div className="flex justify-center pt-8 pb-4">
              <Button
                variant="outline"
                size="lg"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Загрузка…' : 'Показать ещё 20'}
              </Button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
