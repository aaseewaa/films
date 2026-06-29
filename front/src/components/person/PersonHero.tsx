import { Link } from 'react-router-dom';
import type { EntityDetail } from '@/api/types';
import { PageContent } from '@/components/layout/PageContent';
import { useTranslation } from '@/hooks/useTranslation';
import { buildPersonFacts } from '@/lib/personFacts';
import { pluralFilms, pluralSeries } from '@/lib/personFilmographyLine';
import { personHeroPlate } from '@/lib/personHeroTheme';
import { formatPersonRoles } from '@/lib/personRoles';
import { useSiteLang } from '@/lib/siteLang';
import { cn } from '@/lib/utils';

interface PersonHeroProps {
  person: EntityDetail;
}

export function PersonHero({ person }: PersonHeroProps) {
  const tr = useTranslation();
  const locale = useSiteLang();
  const plate = personHeroPlate(person);
  const light = !plate.textLight;

  const facts = buildPersonFacts(person, locale);
  const rolesLine = formatPersonRoles(person, locale);
  const titleEn =
    person.title_en?.trim() &&
    person.title_en.trim().toLowerCase() !== person.title.trim().toLowerCase()
      ? person.title_en.trim()
      : null;

  const workMode: 'director' | 'actor' = person.is_director ? 'director' : 'actor';
  const filmsCount =
    workMode === 'director' ? person.directed_count : person.acted_count;
  const seriesCount = person.series_count ?? 0;

  const photo = person.images.primary || person.images.thumbnail;

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
          <nav className={cn('text-sm sm:text-base shrink-0', textMuted)} aria-label="Breadcrumb">
            <Link to="/" className={cn('transition-colors', linkHover)}>
              {tr('personBreadcrumbHome')}
            </Link>
            <span className="mx-2">»</span>
            <Link to="/search?type=person" className={cn('transition-colors', linkHover)}>
              {tr('personBreadcrumbPeople')}
            </Link>
            <span className="mx-2">»</span>
            <span className={textSoft}>{person.title}</span>
          </nav>

          <div className="flex-1 flex flex-col min-h-0 pt-10 sm:pt-12 lg:pt-16">
            <h1 className="font-serif text-[4.5rem] sm:text-[5.5rem] lg:text-[6.5rem] xl:text-[7.5rem] leading-[1.04] font-bold">
              {person.title}
            </h1>
            {titleEn && (
              <p className={cn('font-sans text-[2.5rem] sm:text-[3rem] lg:text-[3.5rem] mt-2 sm:mt-3', textSoft)}>
                {titleEn}
              </p>
            )}
            {rolesLine && (
              <p className={cn('font-sans text-[2rem] sm:text-[2.25rem] lg:text-[2.5rem] mt-4 sm:mt-6 leading-relaxed', textFaint)}>
                {rolesLine}
              </p>
            )}

            {facts.length > 0 && (
              <div className="mt-8 sm:mt-10 lg:mt-12">
                <h2 className="font-sans text-[2rem] sm:text-[2.25rem] lg:text-[2.5rem] font-semibold mb-4 sm:mb-6">
                  {tr('personFactsHeading')}
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

          {(filmsCount != null && filmsCount > 0) || seriesCount > 0 ? (
            <div
              className={cn(
                'flex flex-wrap gap-x-8 sm:gap-x-12 mt-5 sm:mt-6 pt-4 sm:pt-5 border-t shrink-0',
                borderStat,
              )}
            >
              {filmsCount != null && filmsCount > 0 && (
                <div>
                  <p className="font-serif text-4xl sm:text-5xl lg:text-[3.25rem] leading-none tabular-nums">
                    {filmsCount}
                  </p>
                  <p className={cn('text-base sm:text-lg mt-0.5', textFaint)}>
                    {pluralFilms(filmsCount, locale)}
                  </p>
                </div>
              )}
              {seriesCount > 0 && (
                <div>
                  <p className="font-serif text-4xl sm:text-5xl lg:text-[3.25rem] leading-none tabular-nums">
                    {seriesCount}
                  </p>
                  <p className={cn('text-base sm:text-lg mt-0.5', textFaint)}>
                    {pluralSeries(seriesCount, locale)}
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </div>

        <div className="relative order-1 md:order-2 bg-ink-400 min-h-[min(48rem,88vw)] md:min-h-0 md:h-full">
          {photo ? (
            <img
              src={photo}
              alt={person.title}
              className="absolute inset-0 w-full h-full object-cover object-[center_12%]"
            />
          ) : (
            <div
              className="absolute inset-0 flex items-center justify-center font-serif text-6xl text-white/30"
              aria-hidden
            >
              {person.title.charAt(0)}
            </div>
          )}
        </div>
      </section>
    </PageContent>
  );
}
