import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight } from 'lucide-react';
import {
  getFavorites,
  getHistory,
  getMyRatings,
  getProfileStats,
  getRatingDistribution,
} from '@/api/userData';
import { PageContent } from '@/components/layout/PageContent';
import { ProfileHero } from '@/components/profile/ProfileHero';
import { PosterRow } from '@/components/profile/PosterRow';
import {
  PROFILE_TWIN_PANEL_BODY,
  ProfileSection,
  StatBlock,
} from '@/components/profile/ProfileLayout';
import { RatingHistogram } from '@/components/profile/RatingHistogram';
import {
  ProfileSubNav,
  type ProfileSectionId,
} from '@/components/profile/ProfileSubNav';
import { useAuthStore } from '@/stores/auth';

const SECTION_SCROLL_MT = 'scroll-mt-36 sm:scroll-mt-40';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
  });
}

export function ProfilePage() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const [activeSection, setActiveSection] = useState<ProfileSectionId>('overview');

  const sectionRefs = {
    overview: useRef<HTMLDivElement>(null),
    favorites: useRef<HTMLElement>(null),
    activity: useRef<HTMLElement>(null),
    history: useRef<HTMLElement>(null),
  };

  useEffect(() => {
    if (!isAuthenticated) navigate('/auth/login', { replace: true });
  }, [isAuthenticated, navigate]);

  const statsQ = useQuery({
    queryKey: ['profile', 'stats'],
    queryFn: getProfileStats,
    enabled: isAuthenticated,
  });

  const distQ = useQuery({
    queryKey: ['profile', 'distribution'],
    queryFn: getRatingDistribution,
    enabled: isAuthenticated,
  });

  const favoritesQ = useQuery({
    queryKey: ['profile', 'favorites', 'preview'],
    queryFn: () => getFavorites({ type: 'film', limit: 4 }),
    enabled: isAuthenticated,
  });

  const ratingsQ = useQuery({
    queryKey: ['profile', 'ratings', 'preview'],
    queryFn: () => getMyRatings({ limit: 8 }),
    enabled: isAuthenticated,
  });

  const historyQ = useQuery({
    queryKey: ['profile', 'history', 'preview'],
    queryFn: () => getHistory(8),
    enabled: isAuthenticated,
  });

  function scrollToSection(tab: ProfileSectionId) {
    setActiveSection(tab);
    const el =
      tab === 'overview'
        ? sectionRefs.overview.current
        : sectionRefs[tab].current;
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  const stats = statsQ.data;
  const favoritePosters =
    favoritesQ.data?.items.map((f) => ({
      entity_id: f.entity_id,
      entity_type: f.entity_type,
      title: f.title,
      images: f.images,
      release_year: f.release_year,
    })) ?? [];

  const ratedPosters =
    ratingsQ.data?.items.map((r) => ({
      entity_id: r.entity_id,
      entity_type: r.entity_type,
      title: r.title,
      images: r.images,
      release_year: r.release_year,
      badge: r.rating,
    })) ?? [];

  const recentViews =
    historyQ.data?.views.slice(0, 6).map((v) => ({
      entity_id: v.entity_id,
      entity_type: v.entity_type,
      title: v.title,
      images: v.images,
    })) ?? [];

  const linkClass =
    'text-wine-500 hover:text-wine-600 flex items-center gap-0.5 text-xs sm:text-sm font-semibold uppercase tracking-wider';

  return (
    <div className="bg-site-bg min-h-screen text-ink-500">
      <ProfileHero user={user} stats={stats} />

      {/* Резерв под фото (+15% высоты), чтобы вкладки не наезжали на портрет */}
      <div
        className="hidden md:block h-[clamp(3rem,10vh,8.5rem)] shrink-0 bg-site-bg"
        aria-hidden
      />

      <ProfileSubNav active={activeSection} onTab={scrollToSection} />

      <PageContent className="py-10 sm:py-14 lg:py-16">
        <div ref={sectionRefs.overview} className={SECTION_SCROLL_MT}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-10 sm:mb-12">
            <StatBlock label="Оценки" value={stats?.ratings_count ?? 0} to="/me/ratings" />
            <StatBlock
              label="Избранное"
              value={stats?.favorites_count ?? 0}
              to="/me/favorites"
            />
            <StatBlock label="Просмотрено" value={stats?.watched_count ?? 0} />
            <StatBlock
              label="Хочу посмотреть"
              value={stats?.want_to_watch_count ?? 0}
            />
            <StatBlock label="Просмотры" value={stats?.views_count ?? 0} to="/me/history" />
            <StatBlock label="Поиски" value={stats?.searches_count ?? 0} to="/me/history" />
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-4 sm:gap-5 items-stretch">
          <div
            ref={sectionRefs.favorites}
            className={`${SECTION_SCROLL_MT} h-full min-h-0 flex flex-col`}
          >
          <ProfileSection
            fill
            id="favorites"
            title="Избранное"
            action={
              <Link to="/me/favorites" className={linkClass}>
                Все <ChevronRight size={14} />
              </Link>
            }
          >
            <div className={PROFILE_TWIN_PANEL_BODY}>
              <PosterRow
                twinPanel
                items={favoritePosters}
                emptyLabel="Добавьте фильмы в избранное с карточки фильма"
              />
            </div>
          </ProfileSection>
          </div>

          <div
            ref={sectionRefs.activity}
            className={`${SECTION_SCROLL_MT} h-full min-h-0 flex flex-col`}
          >
          <ProfileSection
            fill
            id="activity"
            title="Активность"
            action={
              <Link to="/me/ratings" className={linkClass}>
                Оценки <ChevronRight size={14} />
              </Link>
            }
          >
            <div className={PROFILE_TWIN_PANEL_BODY}>
              {distQ.isLoading ? (
                <p className="text-sm text-ink-50 h-full flex items-center justify-center">
                  Загрузка…
                </p>
              ) : distQ.data ? (
                <RatingHistogram
                  compact
                  buckets={distQ.data.buckets}
                  total={distQ.data.total}
                  average={distQ.data.average}
                />
              ) : null}
            </div>
          </ProfileSection>
          </div>

          <ProfileSection
            id="ratings"
            title="Недавние оценки"
            action={
              <Link to="/me/ratings" className={linkClass}>
                Все <ChevronRight size={14} />
              </Link>
            }
          >
            <PosterRow
              items={ratedPosters}
              emptyLabel="Оцените фильм на странице карточки"
            />
          </ProfileSection>

          <div ref={sectionRefs.history} className={SECTION_SCROLL_MT}>
          <ProfileSection
            id="history"
            title="История просмотров"
            action={
              <Link to="/me/history" className={linkClass}>
                Вся <ChevronRight size={14} />
              </Link>
            }
          >
            <PosterRow
              items={recentViews}
              emptyLabel="Открывайте карточки фильмов — они появятся здесь"
            />
            {historyQ.data && historyQ.data.searches.length > 0 && (
              <div className="mt-5 pt-4 border-t border-ink-50/15">
                <p className="text-[0.625rem] uppercase tracking-[0.18em] text-ink-50 mb-2">
                  Недавние поиски
                </p>
                <ul className="space-y-1.5">
                  {historyQ.data.searches.slice(0, 4).map((s, i) => (
                    <li key={`${s.query_text}-${i}`} className="flex justify-between text-sm">
                      <Link
                        to={`/search?q=${encodeURIComponent(s.query_text)}`}
                        className="text-wine-500 hover:underline truncate"
                      >
                        {s.query_text}
                      </Link>
                      <span className="text-ink-50 text-xs shrink-0 ml-2">
                        {formatDate(s.searched_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </ProfileSection>
          </div>
        </div>
      </PageContent>
    </div>
  );
}
