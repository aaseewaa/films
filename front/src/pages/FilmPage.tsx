import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getFilm } from '@/api/entity';
import { getRecommendations } from '@/api/recommendations';
import type { FilmDetail } from '@/api/types';
import { cn } from '@/lib/utils';

const TABS = [
  { id: 'about', label: 'О фильме' },
  { id: 'creators', label: 'Создатели и актёры' },
  { id: 'stills', label: 'Кадры' },
  { id: 'articles', label: 'Статьи' },
  { id: 'more', label: 'Ещё' },
] as const;

type TabId = (typeof TABS)[number]['id'];

function formatRating(v: unknown): string | null {
  if (v == null || v === '') return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return n.toFixed(1).replace('.', ',');
}

function buildHeroMeta(film: FilmDetail): string {
  const parts: string[] = [];
  const orig = film.original_title || film.title;
  if (orig) parts.push(orig.toUpperCase());
  if (film.release_year) parts.push(String(film.release_year));
  if (film.genres?.length) {
    parts.push(film.genres.map((g) => g.name.toUpperCase()).join(', '));
  }
  if (film.production_countries) parts.push(film.production_countries.toUpperCase());
  return parts.join(' · ');
}

export function FilmPage() {
  const { id } = useParams();
  const filmId = id ? parseInt(id, 10) : 0;
  const [activeTab, setActiveTab] = useState<TabId>('about');

  const sectionRefs = {
    about: useRef<HTMLElement>(null),
    creators: useRef<HTMLElement>(null),
    stills: useRef<HTMLElement>(null),
    articles: useRef<HTMLElement>(null),
    more: useRef<HTMLElement>(null),
  };

  const { data: film, isLoading, error } = useQuery({
    queryKey: ['film', filmId],
    queryFn: () => getFilm(filmId),
    enabled: filmId > 0,
  });

  const { data: similar } = useQuery({
    queryKey: ['recommendations', 'film', filmId],
    queryFn: () => getRecommendations({ for_film_id: filmId, limit: 8 }),
    enabled: filmId > 0,
  });

  function scrollToTab(tab: TabId) {
    setActiveTab(tab);
    sectionRefs[tab].current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50">
        Загружаем фильм…
      </div>
    );
  }

  if (error || !film) {
    return (
      <div className="max-w-page mx-auto px-6 py-24 text-center text-ink-50">
        Фильм не найден
        <Link to="/films" className="block mt-4 text-wine-500 hover:underline">
          ← К каталогу
        </Link>
      </div>
    );
  }

  const heroImage =
    film.backdrop_url || film.images.primary || film.images.thumbnail || null;
  const voteAvg = formatRating(film.extra_metadata?.vote_average);
  const metaLine = buildHeroMeta(film);

  return (
    <div className="bg-white min-h-screen">
      {/* Хлебные крошки */}
      <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 pt-4 text-sm sm:text-base text-ink-50">
        <Link to="/" className="hover:text-ink-300">
          Главная
        </Link>
        <span className="mx-2">»</span>
        <Link to="/films" className="hover:text-ink-300">
          Фильмы
        </Link>
        <span className="mx-2">»</span>
        <span className="text-ink-300">{film.title}</span>
      </div>

      {/* Hero: кадр из backdrop_url */}
      <section className="relative w-full mt-2 min-h-[min(78vh,720px)] flex items-end overflow-hidden">
        {heroImage ? (
          <img
            src={heroImage}
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-[center_20%]"
          />
        ) : (
          <div className="absolute inset-0 bg-ink-500" />
        )}
        <div
          className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/55 to-black/10"
          aria-hidden
        />

        <div className="relative z-10 w-full px-5 sm:px-10 lg:px-16 xl:px-20 pb-10 sm:pb-14 lg:pb-16 pt-32 text-center text-white">
          <h1 className="font-serif text-[2.5rem] sm:text-6xl lg:text-7xl font-bold leading-[1.05] mb-3 sm:mb-4">
            {film.title}
          </h1>
          <p className="text-xl sm:text-2xl lg:text-[1.65rem] text-white/90 mb-4 sm:mb-5">
            (фильм{film.release_year ? `, ${film.release_year}` : ''})
          </p>
          {metaLine && (
            <p className="text-sm sm:text-base lg:text-lg uppercase tracking-[0.14em] text-white/80 max-w-5xl mx-auto mb-5 sm:mb-6 leading-relaxed">
              {metaLine}
            </p>
          )}
          {film.summary && (
            <p className="text-base sm:text-lg lg:text-xl text-white/95 max-w-3xl mx-auto leading-relaxed line-clamp-4 sm:line-clamp-5">
              {film.summary}
            </p>
          )}
        </div>
      </section>

      {/* Вкладки — на всю ширину */}
      <nav className="sticky top-[4.75rem] lg:top-20 z-30 w-full bg-white border-b border-ink-50/15">
        <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 flex gap-8 sm:gap-12 lg:gap-16 xl:gap-20 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => scrollToTab(tab.id)}
              className={cn(
                'shrink-0 py-5 sm:py-6 text-base sm:text-lg lg:text-xl font-medium border-b-[3px] -mb-px transition-colors whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-ink-500 text-ink-500'
                  : 'border-transparent text-ink-50 hover:text-ink-300',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <div className="w-full px-5 sm:px-10 lg:px-16 xl:px-20 py-10 sm:py-14 lg:py-16 space-y-20 sm:space-y-24 max-w-[1920px] mx-auto">
        {/* О фильме */}
        <section ref={sectionRefs.about} id="about" className="scroll-mt-40">
          <div className="grid lg:grid-cols-[1fr_280px] gap-10 lg:gap-16">
            <div>
              <h2 className="text-base sm:text-lg uppercase tracking-wider text-ink-50 mb-4">
                Оценить фильм
              </h2>
              <div className="flex gap-1 mb-8" aria-hidden>
                {Array.from({ length: 10 }).map((_, i) => (
                  <span
                    key={i}
                    className="w-8 h-8 sm:w-9 sm:h-9 border border-ink-50/25 rounded-sm hover:bg-cream-200 cursor-pointer transition-colors"
                  />
                ))}
              </div>

              {voteAvg && (
                <p className="text-2xl font-bold text-ink-500 mb-6">
                  TMDB: {voteAvg}
                </p>
              )}

              {film.description && (
                <div className="prose-essay text-ink-300 whitespace-pre-line">
                  {film.description}
                </div>
              )}
            </div>

            <aside className="lg:pt-8">
              <h3 className="text-sm uppercase tracking-wider text-ink-50 mb-4">
                Сведения
              </h3>
              <dl className="space-y-3 text-base text-ink-300">
                {film.production_countries && (
                  <>
                    <dt className="text-ink-50 text-sm">Страна</dt>
                    <dd className="mb-2">{film.production_countries}</dd>
                  </>
                )}
                {film.release_year && (
                  <>
                    <dt className="text-ink-50 text-sm">Год</dt>
                    <dd className="mb-2">{film.release_year}</dd>
                  </>
                )}
                {film.genres && film.genres.length > 0 && (
                  <>
                    <dt className="text-ink-50 text-sm">Жанр</dt>
                    <dd className="mb-2">{film.genres.map((g) => g.name).join(', ')}</dd>
                  </>
                )}
                {film.runtime_min != null && (
                  <>
                    <dt className="text-ink-50 text-sm">Длительность</dt>
                    <dd>{film.runtime_min} мин</dd>
                  </>
                )}
              </dl>
            </aside>
          </div>
        </section>

        {/* Создатели */}
        <section ref={sectionRefs.creators} id="creators" className="scroll-mt-40">
          <h2 className="text-2xl font-bold text-ink-500 mb-8">Создатели и актёры</h2>

          {film.directors && film.directors.length > 0 && (
            <div className="mb-10">
              <h3 className="text-sm uppercase tracking-wider text-ink-50 mb-4">
                Режиссёр
              </h3>
              <div className="flex flex-wrap gap-6">
                {film.directors.map((d) => (
                  <PersonChip key={d.id} person={d} />
                ))}
              </div>
            </div>
          )}

          {film.cast && film.cast.length > 0 && (
            <div>
              <h3 className="text-sm uppercase tracking-wider text-ink-50 mb-4">
                В ролях
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
                {film.cast.map((p) => (
                  <PersonChip key={p.id} person={p} showRole />
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Кадры */}
        <section ref={sectionRefs.stills} id="stills" className="scroll-mt-40">
          <h2 className="text-2xl font-bold text-ink-500 mb-8">Кадры</h2>
          {film.stills_urls && film.stills_urls.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
              {film.stills_urls.map((url, i) => (
                <a
                  key={url}
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="block aspect-video overflow-hidden bg-cream-200 hover:opacity-90 transition-opacity"
                >
                  <img
                    src={url}
                    alt={`Кадр ${i + 1}`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </a>
              ))}
            </div>
          ) : (
            <p className="text-ink-50">
              Кадры ещё не загружены. Запустите{' '}
              <code className="text-xs bg-cream-200 px-1">load_tmdb_images</code> на бэке.
            </p>
          )}
        </section>

        {/* Статьи */}
        <section ref={sectionRefs.articles} id="articles" className="scroll-mt-40">
          <h2 className="text-2xl font-bold text-ink-500 mb-4">Статьи</h2>
          <p className="text-ink-50">
            <Link to="/articles" className="text-wine-500 hover:underline">
              Журнал
            </Link>{' '}
            — скоро материалы об этом фильме.
          </p>
        </section>

        {/* Ещё */}
        <section ref={sectionRefs.more} id="more" className="scroll-mt-40">
          <h2 className="text-2xl font-bold text-ink-500 mb-8">Похожие фильмы</h2>
          {similar && similar.items.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
              {similar.items.map((item) => (
                <Link
                  key={item.entity_id}
                  to={`/film/${item.entity_id}`}
                  className="group"
                >
                  {item.images.primary ? (
                    <img
                      src={item.images.primary}
                      alt={item.title}
                      className="w-full aspect-[2/3] object-cover group-hover:opacity-85 transition-opacity"
                    />
                  ) : (
                    <div className="aspect-[2/3] bg-cream-300" />
                  )}
                  <p className="mt-2 text-sm font-medium text-ink-400 line-clamp-2 group-hover:text-ink-500">
                    {item.title}
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-ink-50">Пока нет рекомендаций.</p>
          )}
        </section>
      </div>
    </div>
  );
}

function PersonChip({
  person,
  showRole,
}: {
  person: { id: number; title: string; images: { primary?: string | null }; character_name?: string | null };
  showRole?: boolean;
}) {
  return (
    <Link
      to={`/director/${person.id}`}
      className="flex flex-col items-center text-center group max-w-[120px]"
    >
      {person.images.primary ? (
        <img
          src={person.images.primary}
          alt={person.title}
          className="w-20 h-20 sm:w-24 sm:h-24 rounded-full object-cover mb-2 group-hover:opacity-90"
        />
      ) : (
        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-cream-300 mb-2" />
      )}
      <span className="text-sm font-medium text-ink-400 group-hover:text-ink-500 leading-snug">
        {person.title}
      </span>
      {showRole && person.character_name && (
        <span className="text-xs text-ink-50 mt-0.5 line-clamp-2">{person.character_name}</span>
      )}
    </Link>
  );
}
