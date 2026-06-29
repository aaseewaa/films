import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getEntity } from '@/api/entity';
import { listArticles } from '@/api/articles';
import { listCollections } from '@/api/collections';
import { PageContent } from '@/components/layout/PageContent';
import { PersonAboutPanel } from '@/components/person/PersonAboutPanel';
import { PersonHero } from '@/components/person/PersonHero';
import {
  PersonArticlesPanel,
  PersonAwardsPanel,
  PersonCollectionsPanel,
  PersonFilmographyPanel,
  PersonInfluencesPanel,
} from '@/components/person/PersonSectionPanels';
import {
  PersonSubNav,
  PERSON_TAB_IDS,
  usePersonTabLabels,
  type PersonSectionId,
} from '@/components/person/PersonSubNav';
import { useTranslation } from '@/hooks/useTranslation';
import { orderArticlesForJournal } from '@/lib/articleMosaic';
import { buildPersonBio } from '@/lib/personBio';
import { useSiteLang } from '@/lib/siteLang';
import { useSectionRef } from '@/lib/sectionRef';
import { cn } from '@/lib/utils';

const VALID_TABS = PERSON_TAB_IDS;
const SECTION_SCROLL_MT = 'scroll-mt-44';
const sectionHeading = 'text-4xl sm:text-6xl font-bold text-ink-500 mb-6 sm:mb-8';
const sectionBlock = 'pt-10 sm:pt-12 border-t border-ink-50/15';

function isPersonSectionId(v: string | null): v is PersonSectionId {
  return v != null && (VALID_TABS as readonly string[]).includes(v);
}

export function PersonPage() {
  const lang = useSiteLang();
  const tr = useTranslation();
  const tabLabels = usePersonTabLabels();
  const { id } = useParams();
  const personId = id ? parseInt(id, 10) : 0;
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');

  const [activeSection, setActiveSection] = useState<PersonSectionId>(
    isPersonSectionId(tabParam) ? tabParam : 'about',
  );

  const sectionRefs: Record<PersonSectionId, ReturnType<typeof useSectionRef>> = {
    about: useSectionRef(),
    filmography: useSectionRef(),
    influences: useSectionRef(),
    awards: useSectionRef(),
    articles: useSectionRef(),
    collections: useSectionRef(),
  };

  const { data: person, isLoading, error } = useQuery({
    queryKey: ['entity', personId, lang],
    queryFn: () => getEntity(personId),
    enabled: personId > 0,
  });

  const { data: articlesData } = useQuery({
    queryKey: ['articles', 'person', personId, lang],
    queryFn: () => listArticles({ for_entity_id: personId, limit: 24 }),
    enabled: personId > 0,
  });

  const { data: collectionsData } = useQuery({
    queryKey: ['collections', 'person', personId, lang],
    queryFn: () => listCollections({ for_entity_id: personId, limit: 24 }),
    enabled: personId > 0,
  });

  const bio = useMemo(() => {
    if (!person) return { lead: null, body: null };
    const hasDbAwards = (person.awards?.items?.length ?? 0) > 0;
    return buildPersonBio(person.summary, person.description, {
      dropAwardsSection: hasDbAwards,
    });
  }, [person]);

  const articles = useMemo(
    () => orderArticlesForJournal(articlesData?.items ?? []),
    [articlesData],
  );

  const collections = collectionsData?.items ?? [];
  const filmography = person?.filmography ?? [];
  const awardItems = person?.awards?.items ?? [];

  const isDirector = Boolean(person?.is_director);

  const visibleTabs = useMemo((): PersonSectionId[] => {
    const tabs: PersonSectionId[] = ['about'];
    if (filmography.length > 0) tabs.push('filmography');
    if (isDirector) tabs.push('influences');
    if (awardItems.length > 0) tabs.push('awards');
    if (articles.length > 0) tabs.push('articles');
    if (collections.length > 0) tabs.push('collections');
    return tabs;
  }, [filmography.length, isDirector, awardItems.length, articles.length, collections.length]);

  function scrollToSection(tab: PersonSectionId) {
    if (tab === 'about') {
      sectionRefs.about.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    sectionRefs[tab].current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function selectTab(tab: PersonSectionId) {
    if (!visibleTabs.includes(tab)) return;
    setActiveSection(tab);
    setSearchParams(tab === 'about' ? {} : { tab });
    scrollToSection(tab);
  }

  useEffect(() => {
    if (!person) return;
    if (isPersonSectionId(tabParam) && visibleTabs.includes(tabParam)) {
      setActiveSection(tabParam);
      const t = window.setTimeout(() => scrollToSection(tabParam), 80);
      return () => window.clearTimeout(t);
    }
    if (!visibleTabs.includes(activeSection)) {
      setActiveSection('about');
    }
  }, [person, tabParam, visibleTabs.join(',')]);

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-ink-50">
        {tr('personLoading')}
      </div>
    );
  }

  if (error || !person) {
    return (
      <PageContent className="py-24 text-center text-ink-50">
        {tr('personNotFound')}
        <Link to="/search?type=person" className="block mt-4 text-wine-500 hover:underline">
          {tr('personBackToSearch')}
        </Link>
      </PageContent>
    );
  }

  return (
    <div className="bg-site-bg min-h-screen">
      <PersonHero person={person} />

      <PersonSubNav
        entityId={person.id}
        active={activeSection}
        visibleTabs={visibleTabs}
        onTab={selectTab}
      />

      <PageContent className="py-10 sm:py-14 lg:py-16 space-y-0">
        <section ref={sectionRefs.about} id="about" className={SECTION_SCROLL_MT}>
          <h2 className={sectionHeading}>{tabLabels.about}</h2>
          <PersonAboutPanel bio={bio} filmography={filmography} />
        </section>

        {filmography.length > 0 && (
          <section
            ref={sectionRefs.filmography}
            id="filmography"
            className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
          >
            <h2 className={sectionHeading}>{tabLabels.filmography}</h2>
            <PersonFilmographyPanel items={filmography} />
          </section>
        )}

        {isDirector && (
          <section
            ref={sectionRefs.influences}
            id="influences"
            className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
          >
            <h2 className={cn(sectionHeading, 'sr-only')}>{tabLabels.influences}</h2>
            <PersonInfluencesPanel person={person} />
          </section>
        )}

        {awardItems.length > 0 && (
          <section
            ref={sectionRefs.awards}
            id="awards"
            className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
          >
            <h2 className={sectionHeading}>{tabLabels.awards}</h2>
            <PersonAwardsPanel items={awardItems} />
          </section>
        )}

        {articles.length > 0 && (
          <section
            ref={sectionRefs.articles}
            id="articles"
            className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
          >
            <h2 className={sectionHeading}>{tabLabels.articles}</h2>
            <PersonArticlesPanel articles={articles} />
          </section>
        )}

        {collections.length > 0 && (
          <section
            ref={sectionRefs.collections}
            id="collections"
            className={`${SECTION_SCROLL_MT} ${sectionBlock}`}
          >
            <h2 className={sectionHeading}>{tabLabels.collections}</h2>
            <PersonCollectionsPanel collections={collections} />
          </section>
        )}
      </PageContent>
    </div>
  );
}
