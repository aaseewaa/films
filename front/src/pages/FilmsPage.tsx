import { useEffect, useMemo, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { listFilms, listGenres, listProductionCountries } from '@/api/catalog';
import type { FilmSortBy } from '@/api/types';
import {
  FilmCatalogFilters,
  type FilmFiltersState,
} from '@/components/films/FilmCatalogFilters';
import { FilmCatalogCard } from '@/components/films/FilmCatalogCard';
import { PageContent } from '@/components/layout/PageContent';
import { useSiteLang } from '@/lib/siteLang';

const PAGE_SIZE = 50;
const ANIMATION_GENRE_CODE = 'tmdb-16';

const DEFAULT_FILTERS: FilmFiltersState = {
  catalogType: 'films',
  sortBy: 'popularity',
};

function pluralFilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'фильмов';
  if (mod10 === 1) return 'фильм';
  if (mod10 >= 2 && mod10 <= 4) return 'фильма';
  return 'фильмов';
}

function pluralMultfilms(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'мультфильмов';
  if (mod10 === 1) return 'мультфильм';
  if (mod10 >= 2 && mod10 <= 4) return 'мультфильма';
  return 'мультфильмов';
}

export function FilmsPage() {
  const lang = useSiteLang();
  const [filters, setFilters] = useState<FilmFiltersState>(DEFAULT_FILTERS);

  const filterKey = useMemo(
    () =>
      JSON.stringify({
        catalogType: filters.catalogType,
        genre: filters.genre,
        country: filters.country,
        yearFrom: filters.yearFrom,
        yearTo: filters.yearTo,
        sortBy: filters.sortBy,
      }),
    [filters],
  );

  const hasActiveFilters =
    filters.catalogType !== DEFAULT_FILTERS.catalogType ||
    !!filters.genre ||
    !!filters.country ||
    filters.yearFrom != null ||
    filters.yearTo != null ||
    filters.sortBy !== DEFAULT_FILTERS.sortBy;

  const isAnimation = filters.catalogType === 'animation';

  const { data: genres = [] } = useQuery({
    queryKey: ['genres', lang],
    queryFn: () => listGenres(),
  });

  const filterGenres = useMemo(
    () => genres.filter((g) => g.code !== ANIMATION_GENRE_CODE),
    [genres],
  );

  const { data: countries = [] } = useQuery({
    queryKey: ['production-countries', lang],
    queryFn: () => listProductionCountries(),
  });

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['films', 'catalog', filterKey, lang],
    queryFn: ({ pageParam }) =>
      listFilms({
        catalog: filters.catalogType,
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

  useEffect(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const films = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;
  const loadingAll = isLoading || (hasNextPage && isFetchingNextPage);

  return (
    <div className="bg-site-bg min-h-[calc(100vh-5.75rem)] sm:min-h-[calc(100vh-6rem)] lg:min-h-[calc(100vh-6.5rem)]">
      <PageContent className="py-8 sm:py-12">
        <header className="mb-8 sm:mb-10">
          <h1 className="catalog-pluffy-title mb-2 sm:mb-3">
            {isAnimation ? 'Мультфильмы' : 'Все фильмы'}
          </h1>
          <p className="text-base sm:text-lg text-ink-50">
            {loadingAll
              ? 'Загружаем каталог…'
              : isAnimation
                ? `${total.toLocaleString('ru-RU')} ${pluralMultfilms(total)} в коллекции`
                : `${total.toLocaleString('ru-RU')} ${pluralFilms(total)} в коллекции`}
          </p>
        </header>

        <FilmCatalogFilters
          filters={filters}
          genres={filterGenres}
          countries={countries}
          onChange={setFilters}
          onReset={() => setFilters(DEFAULT_FILTERS)}
          hasActiveFilters={hasActiveFilters}
        />

        <section className="mt-10 sm:mt-12">
          {loadingAll && films.length === 0 && (
            <p className="text-ink-50 py-16 text-center">Загрузка фильмов…</p>
          )}

          {isError && (
            <p className="text-wine-500 py-16 text-center">
              Не удалось загрузить каталог. Проверьте, что бэкенд запущен.
            </p>
          )}

          {!loadingAll && !isError && films.length === 0 && (
            <p className="text-ink-50 py-16 text-center">
              По выбранным фильтрам ничего не найдено.
            </p>
          )}

          {films.map((film) => (
            <FilmCatalogCard key={film.id} film={film} />
          ))}
        </section>
      </PageContent>
    </div>
  );
}
