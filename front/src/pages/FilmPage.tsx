import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getFilm } from '@/api/entity';
import { getRecommendations } from '@/api/recommendations';
import type { FilmDetail } from '@/api/types';
import { FilmAboutPanel } from '@/components/film/FilmAboutPanel';
import { FilmRatingSection } from '@/components/film/FilmRatingSection';
import { FilmCreatorsPanel } from '@/components/film/FilmCreatorsPanel';
import { FilmCreatorsPreview } from '@/components/film/FilmCreatorsPreview';
import {
  FilmArticlesPanel,
  FilmAwardsPanel,
  FilmSimilarPanel,
  FilmStillsPanel,
} from '@/components/film/FilmSectionPanels';
import { FilmSubNav, type FilmSectionId } from '@/components/film/FilmSubNav';
import { PageContent } from '@/components/layout/PageContent';
import { useTranslation } from '@/hooks/useTranslation';
import { useSiteLang } from '@/lib/siteLang';
import { resolveFilmHeroImage } from '@/lib/filmHero';
import { useSectionRef } from '@/lib/sectionRef';

const VALID_TABS: FilmSectionId[] = [
  'about',
  'creators',
  'stills',
  'articles',
  'similar',
  'awards',
];

const SECTION_SCROLL_MT = 'scroll-mt-44';

function isFilmSectionId(v: string | null): v is FilmSectionId {
  return v != null && VALID_TABS.includes(v as FilmSectionId);
}

function formatRating(v: unknown): string | null {
  if (v == null || v === '') return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return n.toFixed(1).replace('.', ',');
}

function mediaKindLabel(
  film: FilmDetail,
  labels: { film: string; series: string; animation?: string },
): string {
  const kind = film.media_kind;
  if (kind === 'сериал') return labels.series;
  if (kind === 'мультфильм' && labels.animation) return labels.animation;
  return labels.film;
}

function aboutTextBlocks(film: FilmDetail): { lead: string | null; body: string | null } {
  const summary = film.summary?.trim() ?? '';
  const description = film.description?.trim() ?? '';
  if (!summary && !description) return { lead: null, body: null };
  if (!summary) return { lead: null, body: description };
  if (!description) return { lead: summary, body: null };
  if (summary === description) return { lead: summary, body: null };
  if (description.startsWith(summary)) return { lead: null, body: description };
  return { lead: summary, body: description };
}

function buildHeroMeta(film: FilmDetail): string {
  const parts: string[] = [];
  const orig = film.original_title?.trim();
  if (orig) parts.push(orig.toUpperCase());
  if (film.release_year) parts.push(String(film.release_year));
  const genres = film.genres?.slice(0, 3) ?? [];
  if (genres.length) {
    parts.push(genres.map((g) => g.name.toUpperCase()).join(', '));
  }
  const country = film.production_countries?.split(',')[0]?.trim();
  if (country) parts.push(country.toUpperCase());
  const age = film.age_rating?.trim();
  if (age) parts.push(age);
  return parts.join(' · ');
}

export function FilmPage() {
  const lang = useSiteLang();
  const tr = useTranslation();
  const { id } = useParams();
  const filmId = id ? parseInt(id, 10) : 0;
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');

  const [activeSection, setActiveSection] = useState<FilmSectionId>(
    isFilmSectionId(tabParam) ? tabParam : 'about',
  );
  const [moreOpen, setMoreOpen] = useState(false);

  const sectionRefs: Record<FilmSectionId, ReturnType<typeof useSectionRef>> = {
    about: useSectionRef(),
    creators: useSectionRef(),
    stills: useSectionRef(),
    articles: useSectionRef(),
    similar: useSectionRef(),
    awards: useSectionRef(),
  };

  const { data: film, isLoading, error } = useQuery({
    queryKey: ['film', filmId, lang],
    queryFn: () => getFilm(filmId),
    enabled: filmId > 0,
  });

  const { data: similar } = useQuery({
    queryKey: ['recommendations', 'film', filmId, lang],
    queryFn: () => getRecommendations({ for_film_id: filmId, limit: 8 }),
    enabled: filmId > 0,
  });

  function scrollToSection(tab: FilmSectionId) {
    if (tab === 'about') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    sectionRefs[tab].current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function openCreatorsFull() {
    setActiveSection('creators');
    setMoreOpen(false);
    setSearchParams({ tab: 'creators' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function backToFilm() {
    setActiveSection('about');
    setSearchParams({});
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function selectTab(tab: FilmSectionId) {
    setActiveSection(tab);
    setMoreOpen(false);
    if (tab === 'about') {
      setSearchParams({});
      scrollToSection('about');
      return;
    }
    if (tab === 'creators') {
      openCreatorsFull();
      return;
    }
    setSearchParams({ tab });
    scrollToSection(tab);
  }

  const creatorsFullView = tabParam === 'creators';

  useEffect(() => {
    if (!film || !isFilmSectionId(tabParam)) return;
    setActiveSection(tabParam);
    if (tabParam === 'creators') return;
    const t = window.setTimeout(() => scrollToSection(tabParam), 80);
    return () => window.clearTimeout(t);
  }, [film, tabParam]);

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50">
        Загружаем фильм…
      </div>
    );
  }

  if (error || !film) {
    return (
      <PageContent className="py-24 text-center text-ink-50">
        Фильм не найден
        <Link to="/films" className="block mt-4 text-wine-500 hover:underline">
          ← К каталогу
        </Link>
      </PageContent>
    );
  }

  const heroImage = resolveFilmHeroImage(film);
  const voteAvg = formatRating(film.extra_metadata?.vote_average);
  const metaLine = buildHeroMeta(film);
  const aboutText = aboutTextBlocks(film);
  const kindLabel = mediaKindLabel(film, {
    film: tr('mediaFilm'),
    series: tr('mediaSeries'),
  });
  const hasCrew = (film.directors?.length ?? 0) > 0 || (film.cast?.length ?? 0) > 0;

  const sectionHeading = 'text-4xl sm:text-6xl font-bold text-ink-500 mb-6 sm:mb-8';
  const sectionBlock = 'pt-10 sm:pt-12 border-t border-ink-50/15';

  return (
    <div className="bg-site-bg min-h-screen">
      <PageContent className="pt-4 pb-2 text-sm sm:text-base text-ink-50">
        <Link to="/" className="hover:text-ink-300">
          Главная
        </Link>
        <span className="mx-2">»</span>
        <Link to="/films" className="hover:text-ink-300">
          Фильмы
        </Link>
        <span className="mx-2">»</span>
        <span className="text-ink-300">{film.title}</span>
      </PageContent>

      {!creatorsFullView && (
      <PageContent className="mt-2">
        <section className="relative w-full min-h-[min(156vh,1440px)] flex items-end overflow-hidden bg-black">
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

          <div className="relative z-10 w-full px-2 sm:px-4 pb-24 sm:pb-32 md:pb-40 lg:pb-48 xl:pb-56 pt-28 sm:pt-32 text-center">
            <h1 className="font-serif text-4xl sm:text-6xl md:text-7xl lg:text-8xl xl:text-[5.25rem] font-bold leading-[1.08] text-white">
              {film.title}
            </h1>
            <p className="font-serif text-2xl sm:text-4xl md:text-5xl lg:text-6xl text-white mt-2 sm:mt-3 leading-tight">
              ({kindLabel}
              {film.release_year ? `, ${film.release_year}` : ''})
            </p>
            {metaLine && (
              <p className="mt-4 sm:mt-5 text-xs sm:text-sm md:text-base uppercase tracking-[0.12em] sm:tracking-[0.14em] text-white leading-relaxed max-w-5xl mx-auto">
                {metaLine}
              </p>
            )}
          </div>
        </section>
      </PageContent>
      )}

      {creatorsFullView && (
        <PageContent className="pt-6 sm:pt-8 pb-2">
          <button
            type="button"
            onClick={backToFilm}
            className="text-lg sm:text-xl lg:text-2xl text-ink-50 hover:text-ink-500 transition-colors"
          >
            ← К фильму «{film.title}»
          </button>
        </PageContent>
      )}

      <FilmSubNav
        entityId={film.id}
        active={activeSection}
        moreOpen={moreOpen}
        onTab={selectTab}
        onMoreToggle={() => setMoreOpen((v) => !v)}
        onMoreClose={() => setMoreOpen(false)}
      />

      <PageContent className="film-page-body py-10 sm:py-14 lg:py-16 space-y-0">
        {creatorsFullView && hasCrew ? (
          <FilmCreatorsPanel film={film} metaLine={metaLine} />
        ) : (
          <>
            <section
              ref={sectionRefs.about}
              id="about"
              className={SECTION_SCROLL_MT}
            >
              <h2 className={sectionHeading}>О фильме</h2>
              <FilmAboutPanel film={film} aboutText={aboutText} />
              <FilmRatingSection entityId={film.id} voteAvg={voteAvg} />
            </section>

            {hasCrew && (
              <section
                ref={sectionRefs.creators}
                id="creators"
                className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
              >
                <FilmCreatorsPreview
                  directors={film.directors ?? []}
                  cast={film.cast ?? []}
                  onOpenAll={openCreatorsFull}
                />
              </section>
            )}

            <section
              ref={sectionRefs.stills}
              id="stills"
              className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
            >
              <h2 className={sectionHeading}>Кадры</h2>
              <FilmStillsPanel film={film} />
            </section>

            <section
              ref={sectionRefs.articles}
              id="articles"
              className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
            >
              <h2 className={sectionHeading}>Статьи</h2>
              <FilmArticlesPanel />
            </section>

            <section
              ref={sectionRefs.similar}
              id="similar"
              className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
            >
              <h2 className={sectionHeading}>Похожие фильмы</h2>
              <FilmSimilarPanel items={similar?.items ?? []} />
            </section>

            <section
              ref={sectionRefs.awards}
              id="awards"
              className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
            >
              <h2 className={sectionHeading}>Награды</h2>
              <FilmAwardsPanel />
            </section>
          </>
        )}
      </PageContent>
    </div>
  );
}
