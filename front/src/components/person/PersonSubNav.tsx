import { useMemo } from 'react';
import { PageContent } from '@/components/layout/PageContent';
import { FavoriteButton } from '@/components/user/FavoriteButton';
import { useTranslation } from '@/hooks/useTranslation';
import type { UiKey } from '@/lib/i18n';
import { cn } from '@/lib/utils';

export const PERSON_TAB_IDS = [
  'about',
  'filmography',
  'influences',
  'awards',
  'articles',
  'collections',
] as const;

export type PersonSectionId = (typeof PERSON_TAB_IDS)[number];

const TAB_LABEL_KEYS: Record<PersonSectionId, UiKey> = {
  about: 'personTabAbout',
  filmography: 'personTabFilmography',
  influences: 'personTabInfluences',
  awards: 'personTabAwards',
  articles: 'personTabArticles',
  collections: 'personTabCollections',
};

export function usePersonTabLabels(): Record<PersonSectionId, string> {
  const tr = useTranslation();
  return useMemo(
    () =>
      Object.fromEntries(
        PERSON_TAB_IDS.map((id) => [id, tr(TAB_LABEL_KEYS[id])]),
      ) as Record<PersonSectionId, string>,
    [tr],
  );
}

export function usePersonTabLabel(id: PersonSectionId): string {
  const tr = useTranslation();
  return tr(TAB_LABEL_KEYS[id]);
}

const TAB_CLASS =
  'text-2xl sm:text-3xl lg:text-4xl xl:text-[2.75rem] font-medium transition-colors whitespace-nowrap';

interface PersonSubNavProps {
  entityId: number;
  active: PersonSectionId;
  visibleTabs: PersonSectionId[];
  onTab: (tab: PersonSectionId) => void;
}

export function PersonSubNav({ entityId, active, visibleTabs, onTab }: PersonSubNavProps) {
  const tr = useTranslation();

  const tabs = useMemo(
    () =>
      PERSON_TAB_IDS.filter((id) => visibleTabs.includes(id)).map((id) => ({
        id,
        label: tr(TAB_LABEL_KEYS[id]),
      })),
    [tr, visibleTabs],
  );

  return (
    <nav className="sticky top-[5.75rem] sm:top-[6rem] lg:top-[6.5rem] z-30 w-full bg-site-bg border-b border-ink-50/15">
      <PageContent className="py-4 sm:py-5 lg:py-6">
        <div className="relative flex flex-wrap items-center justify-center gap-x-3 sm:gap-x-5 lg:gap-x-7 text-ink-500">
          {tabs.map((tab, index) => (
            <span key={tab.id} className="inline-flex items-center gap-x-3 sm:gap-x-5 lg:gap-x-7">
              {index > 0 && (
                <span className="text-ink-50/70 font-light select-none" aria-hidden>
                  |
                </span>
              )}
              <button
                type="button"
                onClick={() => onTab(tab.id)}
                className={cn(
                  TAB_CLASS,
                  active === tab.id ? 'text-ink-500' : 'text-ink-50 hover:text-ink-300',
                )}
              >
                {tab.label}
              </button>
            </span>
          ))}

          {entityId > 0 && (
            <div className="w-full flex justify-center mt-4 sm:mt-0 sm:w-auto sm:absolute sm:right-0 sm:top-1/2 sm:-translate-y-1/2">
              <FavoriteButton entityId={entityId} />
            </div>
          )}
        </div>
      </PageContent>
    </nav>
  );
}
