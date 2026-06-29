import { Link } from 'react-router-dom';
import type { User } from '@/api/types';
import type { ProfileStats } from '@/api/userData';
import { PageContent } from '@/components/layout/PageContent';
import { ProfileAvatarHero } from '@/components/profile/ProfileAvatarHero';
import { pluralFilms } from '@/lib/personFilmographyLine';
import { profileHeroPlate } from '@/lib/personHeroTheme';
import { useSiteLang } from '@/lib/siteLang';
import type { SiteLocale } from '@/stores/locale';
import { cn } from '@/lib/utils';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function pluralRatings(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'оценок';
  if (mod10 === 1) return 'оценка';
  if (mod10 >= 2 && mod10 <= 4) return 'оценки';
  return 'оценок';
}

function pluralViews(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'просмотров';
  if (mod10 === 1) return 'просмотр';
  if (mod10 >= 2 && mod10 <= 4) return 'просмотра';
  return 'просмотров';
}

function pluralSearches(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return 'поисков';
  if (mod10 === 1) return 'поиск';
  if (mod10 >= 2 && mod10 <= 4) return 'поиска';
  return 'поисков';
}

interface ProfileHeroMetric {
  value: number;
  label: string;
}

function buildHeroMetrics(stats: ProfileStats | null | undefined, locale: SiteLocale): ProfileHeroMetric[] {
  if (!stats) return [];
  const items: ProfileHeroMetric[] = [];
  if (stats.ratings_count > 0) {
    items.push({ value: stats.ratings_count, label: pluralRatings(stats.ratings_count) });
  }
  if (stats.favorites_count > 0) {
    items.push({ value: stats.favorites_count, label: 'в избранном' });
  }
  if (stats.watched_count > 0) {
    items.push({
      value: stats.watched_count,
      label: `${pluralFilms(stats.watched_count, locale)} просмотрено`,
    });
  }
  if (stats.want_to_watch_count > 0) {
    items.push({
      value: stats.want_to_watch_count,
      label: `${pluralFilms(stats.want_to_watch_count, locale)} в планах`,
    });
  }
  if (stats.views_count > 0) {
    items.push({ value: stats.views_count, label: pluralViews(stats.views_count) });
  }
  if (stats.searches_count > 0) {
    items.push({ value: stats.searches_count, label: pluralSearches(stats.searches_count) });
  }
  return items;
}

interface ProfileHeroProps {
  user: User;
  stats?: ProfileStats | null;
}

export function ProfileHero({ user, stats }: ProfileHeroProps) {
  const locale = useSiteLang();
  const plate = profileHeroPlate(user);
  const light = !plate.textLight;

  const facts: { label: string; value: string }[] = [];
  if (user.email) facts.push({ label: 'Email', value: user.email });
  if (user.city?.trim()) facts.push({ label: 'Город', value: user.city.trim() });
  if (user.registered_at) {
    facts.push({ label: 'На сайте с', value: formatDate(user.registered_at) });
  }

  const metrics = buildHeroMetrics(stats, locale);

  const textMain = light ? 'text-ink-400' : 'text-white';
  const textMuted = light ? 'text-ink-50' : 'text-white/70';
  const textSoft = light ? 'text-ink-100' : 'text-white/90';
  const textFaint = light ? 'text-ink-50' : 'text-white/80';
  const labelMuted = light ? 'text-ink-50' : 'text-white/75';
  const borderStat = light ? 'border-ink-50/30' : 'border-white/20';
  const linkHover = light ? 'hover:text-ink-300' : 'hover:text-white';

  return (
    <PageContent className="pt-2 sm:pt-3 pb-0">
      <section
        className={cn(
          'grid grid-cols-1 overflow-hidden rounded-sm',
          'md:grid-cols-[3fr_2fr]',
          'md:h-[75rem]',
          'lg:h-[78rem]',
        )}
      >
        <div
          className={cn(
            'flex flex-col justify-between px-6 sm:px-8 lg:px-11 py-6 sm:py-7 lg:py-8 order-2 md:order-1 min-h-0',
            textMain,
          )}
          style={{ backgroundColor: plate.bg }}
        >
          <nav className={cn('text-sm sm:text-base shrink-0', textMuted)} aria-label="Хлебные крошки">
            <Link to="/" className={cn('transition-colors', linkHover)}>
              Главная
            </Link>
            <span className="mx-2">»</span>
            <span className={textSoft}>Профиль</span>
          </nav>

          <div className="flex-1 flex flex-col min-h-0 pt-10 sm:pt-12 lg:pt-16">
            <h1 className="font-serif text-[4.5rem] sm:text-[5.5rem] lg:text-[6.5rem] xl:text-[7.5rem] leading-[1.04] font-bold">
              {user.display_name}
            </h1>
            <p className={cn('font-sans text-[2rem] sm:text-[2.25rem] lg:text-[2.5rem] mt-4 sm:mt-6 leading-relaxed', textFaint)}>
              Личный кабинет
            </p>

            {facts.length > 0 && (
              <div className="mt-8 sm:mt-10 lg:mt-12">
                <h2 className="font-sans text-[2rem] sm:text-[2.25rem] lg:text-[2.5rem] font-semibold mb-4 sm:mb-6">
                  Сведения
                </h2>
                <ul className="space-y-3 sm:space-y-4 text-[2rem] sm:text-[2.25rem] lg:text-[2.5rem] list-none leading-snug">
                  {facts.map((row) => (
                    <li key={row.label} className="flex flex-wrap gap-x-2 gap-y-0.5">
                      <span className={cn('shrink-0', labelMuted)}>{row.label}</span>
                      <span>{row.value}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {metrics.length > 0 && (
            <div
              className={cn(
                'flex flex-wrap gap-x-8 sm:gap-x-12 mt-5 sm:mt-6 pt-4 sm:pt-5 border-t shrink-0',
                borderStat,
              )}
            >
              {metrics.map((m) => (
                <div key={m.label}>
                  <p className="font-serif text-4xl sm:text-5xl lg:text-[3.25rem] leading-none tabular-nums">
                    {m.value}
                  </p>
                  <p className={cn('text-base sm:text-lg mt-0.5', textFaint)}>{m.label}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="relative order-1 md:order-2 min-h-[min(48rem,88vw)] md:min-h-0 md:h-full bg-ink-400">
          <ProfileAvatarHero
            avatarUrl={user.avatar_url}
            displayName={user.display_name}
          />
        </div>
      </section>
    </PageContent>
  );
}
