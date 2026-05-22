import { useEffect, useMemo, useRef } from 'react';
import { PageContent } from '@/components/layout/PageContent';
import { FavoriteButton } from '@/components/user/FavoriteButton';
import { useTranslation } from '@/hooks/useTranslation';
import { cn } from '@/lib/utils';

export const FILM_MAIN_TAB_IDS = ['about', 'creators', 'stills', 'articles'] as const;
export const FILM_MORE_TAB_IDS = ['similar', 'awards'] as const;

export type FilmMainTabId = (typeof FILM_MAIN_TAB_IDS)[number];
export type FilmMoreTabId = (typeof FILM_MORE_TAB_IDS)[number];
export type FilmSectionId = FilmMainTabId | FilmMoreTabId;

const TAB_CLASS =
  'text-2xl sm:text-3xl lg:text-4xl xl:text-[2.75rem] font-medium transition-colors whitespace-nowrap';

interface FilmSubNavProps {
  entityId: number;
  active: FilmSectionId;
  moreOpen: boolean;
  onTab: (tab: FilmSectionId) => void;
  onMoreToggle: () => void;
  onMoreClose: () => void;
}

export function FilmSubNav({
  entityId,
  active,
  moreOpen,
  onTab,
  onMoreToggle,
  onMoreClose,
}: FilmSubNavProps) {
  const tr = useTranslation();
  const moreRef = useRef<HTMLDivElement>(null);

  const mainTabs = useMemo(
    () =>
      [
        { id: 'about' as const, label: tr('filmTabAbout') },
        { id: 'creators' as const, label: tr('filmTabCreators') },
        { id: 'stills' as const, label: tr('filmTabStills') },
        { id: 'articles' as const, label: tr('filmTabArticles') },
      ],
    [tr],
  );

  const moreItems = useMemo(
    () =>
      [
        { id: 'similar' as const, label: tr('filmTabSimilar') },
        { id: 'awards' as const, label: tr('filmTabAwards') },
      ],
    [tr],
  );

  const moreActive = moreItems.some((item) => item.id === active);

  useEffect(() => {
    if (!moreOpen) return;
    function onPointerDown(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        onMoreClose();
      }
    }
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [moreOpen, onMoreClose]);

  return (
    <nav className="sticky top-[5.75rem] sm:top-[6rem] lg:top-[6.5rem] z-30 w-full bg-site-bg border-b border-ink-50/15">
      <PageContent className="py-6 sm:py-8 lg:py-10">
        <div className="relative flex flex-wrap items-center justify-center gap-x-3 sm:gap-x-5 lg:gap-x-7 text-ink-500">
          {mainTabs.map((tab, index) => (
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

          <span className="text-ink-50/70 font-light select-none" aria-hidden>
            |
          </span>

          <div ref={moreRef} className="relative inline-flex">
            <button
              type="button"
              onClick={onMoreToggle}
              aria-expanded={moreOpen}
              aria-haspopup="true"
              className={cn(
                TAB_CLASS,
                moreActive || moreOpen ? 'text-ink-500' : 'text-ink-50 hover:text-ink-300',
              )}
            >
              {tr('filmMore')}
            </button>

            {moreOpen && (
              <div
                role="menu"
                className="absolute left-1/2 -translate-x-1/2 top-full mt-3 min-w-[14rem] bg-site-bg border border-ink-50/20 shadow-lg py-2 z-40"
              >
                {moreItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="menuitem"
                    onClick={() => onTab(item.id)}
                    className={cn(
                      'block w-full text-left px-5 py-2.5 text-lg sm:text-xl transition-colors',
                      active === item.id
                        ? 'text-ink-500 bg-site-hover'
                        : 'text-ink-300 hover:bg-site-hover hover:text-ink-500',
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>

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
