import { PageContent } from '@/components/layout/PageContent';
import { cn } from '@/lib/utils';

export const PROFILE_TABS = [
  { id: 'overview', label: 'Обзор' },
  { id: 'favorites', label: 'Избранное' },
  { id: 'activity', label: 'Оценки' },
  { id: 'history', label: 'История' },
] as const;

export type ProfileSectionId = (typeof PROFILE_TABS)[number]['id'];

const TAB_CLASS =
  'text-2xl sm:text-3xl lg:text-4xl xl:text-[2.75rem] font-medium transition-colors whitespace-nowrap';

interface ProfileSubNavProps {
  active: ProfileSectionId;
  onTab: (tab: ProfileSectionId) => void;
}

export function ProfileSubNav({ active, onTab }: ProfileSubNavProps) {
  return (
    <nav className="sticky top-[5.75rem] sm:top-[6rem] lg:top-[6.5rem] z-30 w-full bg-site-bg border-b border-ink-50/15">
      <PageContent className="py-4 sm:py-5 lg:py-6">
        <div className="flex flex-wrap items-center justify-center gap-x-3 sm:gap-x-5 lg:gap-x-7 text-ink-500">
          {PROFILE_TABS.map((tab, index) => (
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
        </div>
      </PageContent>
    </nav>
  );
}
