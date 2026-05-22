import { PageContent } from '@/components/layout/PageContent';
import { FavoriteButton } from '@/components/user/FavoriteButton';
import { cn } from '@/lib/utils';

export const PERSON_TABS = [
  { id: 'about', label: 'О персоне' },
  { id: 'filmography', label: 'Фильмография' },
  { id: 'influences', label: 'Учителя / вдохновители' },
  { id: 'awards', label: 'Награды' },
  { id: 'articles', label: 'Публикации' },
  { id: 'collections', label: 'Подборки' },
] as const;

export type PersonSectionId = (typeof PERSON_TABS)[number]['id'];

const TAB_CLASS =
  'text-2xl sm:text-3xl lg:text-4xl xl:text-[2.75rem] font-medium transition-colors whitespace-nowrap';

interface PersonSubNavProps {
  entityId: number;
  active: PersonSectionId;
  visibleTabs: PersonSectionId[];
  onTab: (tab: PersonSectionId) => void;
}

export function PersonSubNav({ entityId, active, visibleTabs, onTab }: PersonSubNavProps) {
  const tabs = PERSON_TABS.filter((t) => visibleTabs.includes(t.id));

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
