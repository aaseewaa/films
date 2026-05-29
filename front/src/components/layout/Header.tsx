import { Fragment, useMemo, useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogIn, LogOut, Heart, Star, History } from 'lucide-react';
import { Logo } from './Logo';
import { HeaderMenuToggle } from './HeaderMenuToggle';
import { ExpandableSearch } from './ExpandableSearch';
import { LanguageToggle } from './LanguageToggle';
import { useAuthStore } from '@/stores/auth';
import { useTranslation } from '@/hooks/useTranslation';
import { cn } from '@/lib/utils';
import { SITE_GUTTER_CLASS } from '@/lib/siteGutter';

type NavItem =
  | { to: string; label: string }
  | { to: string; lines: readonly [string, string] };

function isNavActive(pathname: string, to: string): boolean {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
}

function NavItemLabel({ item }: { item: NavItem }) {
  if ('lines' in item) {
    return (
      <span className="inline-flex flex-col items-center justify-center leading-[1.05] text-center whitespace-nowrap">
        <span>{item.lines[0]}</span>
        <span>{item.lines[1]}</span>
      </span>
    );
  }
  return <span className="whitespace-nowrap">{item.label}</span>;
}

const MENU_SECTION_TITLE_CLASS =
  'font-sans text-4xl sm:text-5xl lg:text-[3.25rem] xl:text-[3.5rem] font-bold leading-tight text-[#0ABAB5] mb-5 sm:mb-6';

/** Высота шапки для calc(100vh - …) на главной */
export const HEADER_HEIGHT_CLASS = 'min-h-[5.75rem] sm:min-h-[6rem] lg:min-h-[6.5rem]';

/**
 * Шапка в духе kinomania: белый фон, бургер + крупный логотип слева,
 * крупные пункты меню и лупа справа. Бургер открывает полноэкранное меню.
 */
export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const tr = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const { isAuthenticated, user, logout } = useAuthStore();

  const navItems = useMemo<NavItem[]>(
    () => [
      { to: '/films', label: tr('navFilms') },
      { to: '/collections', label: tr('navCollections') },
      { to: '/articles', label: tr('navArticles') },
      { to: '/news', label: tr('navNews') },
      { to: '/', lines: [tr('navGeniuses'), tr('navInspirers')] },
    ],
    [tr],
  );

  const fullMenuSections = useMemo(
    () => [
      {
        title: tr('navGeniuses'),
        links: [{ to: '/', label: tr('menuGraph') }],
      },
      {
        title: tr('navFilms'),
        links: [{ to: '/films', label: tr('menuAllFilms') }],
      },
      {
        title: tr('navCollections'),
        links: [{ to: '/collections', label: tr('menuAllCollections') }],
      },
      {
        title: tr('navArticles'),
        links: [
          { to: '/articles', label: tr('menuJournal') },
          { to: '/article/hitchcock-arhitektor-trevogi', label: tr('menuEditorial') },
        ],
      },
      {
        title: tr('navNews'),
        links: [{ to: '/news', label: tr('menuShowtimes') }],
      },
      {
        title: 'about',
        links: [{ to: '/about', label: tr('menuAbout') }],
      },
    ],
    [tr],
  );

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setMenuOpen(false);
    }
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <>
      <header className="sticky top-0 z-50 bg-site-bg border-b border-ink-50/12">
        <div
          className={cn(
            'flex items-center justify-between gap-4 lg:gap-6',
            'pt-3 pb-2 sm:pt-3.5 sm:pb-2.5',
            SITE_GUTTER_CLASS,
            HEADER_HEIGHT_CLASS,
          )}
        >
          <div className="flex items-center gap-3 sm:gap-5 lg:gap-8 min-w-0 shrink-0">
            <HeaderMenuToggle
              open={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            />
            <Logo size="large" className="shrink min-w-0" />
          </div>

          <div className="hidden md:flex items-center justify-end flex-1 min-w-0 gap-4 lg:gap-5 overflow-hidden">
            <nav
              className={cn(
                'flex flex-nowrap items-center justify-end shrink-0',
                'transition-transform duration-300 ease-out',
                searchExpanded && '-translate-x-1',
              )}
              aria-label="Основное меню"
            >
              {navItems.map((item, index) => (
                <Fragment key={item.to}>
                  {index > 0 && (
                    <span
                      className="shrink-0 px-3 lg:px-5 xl:px-7 text-ink-500 font-semibold text-[1.6rem] lg:text-[1.95rem] xl:text-[2.25rem] leading-none select-none"
                      aria-hidden
                    >
                      |
                    </span>
                  )}
                  <Link
                    to={item.to}
                    className={cn(
                      'shrink-0 uppercase font-semibold tracking-[0.06em] text-ink-500',
                      'text-[1.6rem] lg:text-[1.95rem] xl:text-[2.25rem] leading-none',
                      'px-2.5 lg:px-3.5 py-1.5 rounded-sm transition-colors duration-150',
                      'hover:text-[#0ABAB5]',
                    )}
                    aria-current={
                      isNavActive(location.pathname, item.to) ? 'page' : undefined
                    }
                  >
                    <NavItemLabel item={item} />
                  </Link>
                </Fragment>
              ))}
            </nav>

            <span
              className="shrink-0 px-3 lg:px-5 xl:px-7 text-ink-500 font-semibold text-[1.6rem] lg:text-[1.95rem] xl:text-[2.25rem] leading-none select-none"
              aria-hidden
            >
              |
            </span>

            <ExpandableSearch onExpandedChange={setSearchExpanded} />

            <span
              className="shrink-0 px-3 lg:px-5 xl:px-7 text-ink-500 font-semibold text-[1.6rem] lg:text-[1.95rem] xl:text-[2.25rem] leading-none select-none"
              aria-hidden
            >
              |
            </span>

            <LanguageToggle />
          </div>

          <div className="md:hidden flex items-center gap-3 shrink-0">
            <LanguageToggle />
            <button
              type="button"
              onClick={() => navigate('/search')}
              className="p-1 rounded-sm text-ink-500 hover:text-ink-400 hover:bg-site-hover transition-colors"
              aria-label={tr('searchAria')}
            >
            <svg
              width="26"
              height="26"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              aria-hidden
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20 16 16" />
            </svg>
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div
          className="fixed inset-x-0 bottom-0 z-40 bg-[#E1EFF6] overflow-y-auto top-[5.75rem] sm:top-[6rem] lg:top-[6.5rem]"
          role="dialog"
          aria-modal="true"
          aria-label="Меню сайта"
        >
          <div
            className={cn(
              SITE_GUTTER_CLASS,
              'pt-16 sm:pt-20 lg:pt-24 pb-10 sm:pb-12 lg:pb-16 min-h-full',
            )}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-10 gap-y-20 sm:gap-y-24 lg:gap-y-28">
              {fullMenuSections.map((section) => (
                <div key={section.title}>
                  <h2 className={MENU_SECTION_TITLE_CLASS}>{section.title}</h2>
                  <ul className="space-y-3 sm:space-y-4">
                    {section.links.map((link) => (
                      <li key={link.to + link.label}>
                        <Link
                          to={link.to}
                          onClick={closeMenu}
                          className="uppercase text-sm sm:text-[0.95rem] font-semibold tracking-[0.12em] text-ink-500 hover:text-ink-400 transition-colors"
                        >
                          {link.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}

              <div>
                {isAuthenticated && user ? (
                  <Link
                    to="/me"
                    onClick={closeMenu}
                    className={cn(
                      MENU_SECTION_TITLE_CLASS,
                      'inline-block hover:text-ink-400 transition-colors',
                    )}
                  >
                    {tr('menuProfile')}
                  </Link>
                ) : (
                  <h2 className={MENU_SECTION_TITLE_CLASS}>{tr('menuProfile')}</h2>
                )}
                {isAuthenticated && user ? (
                  <ul className="space-y-3 sm:space-y-4">
                    <li>
                      <MenuAccountLink
                        to="/me/favorites"
                        icon={<Heart size={18} />}
                        onClick={closeMenu}
                      >
                        {tr('menuFavorites')}
                      </MenuAccountLink>
                    </li>
                    <li>
                      <MenuAccountLink
                        to="/me/ratings"
                        icon={<Star size={18} />}
                        onClick={closeMenu}
                      >
                        {tr('menuRatings')}
                      </MenuAccountLink>
                    </li>
                    <li>
                      <MenuAccountLink
                        to="/me/history"
                        icon={<History size={18} />}
                        onClick={closeMenu}
                      >
                        {tr('menuHistory')}
                      </MenuAccountLink>
                    </li>
                    <li>
                      <button
                        type="button"
                        onClick={() => {
                          logout();
                          closeMenu();
                        }}
                        className="flex items-center gap-3 uppercase text-sm sm:text-[0.95rem] font-semibold tracking-[0.12em] text-ink-500 hover:text-ink-400 transition-colors"
                      >
                        <LogOut size={18} />
                        {tr('menuLogout')}
                      </button>
                    </li>
                  </ul>
                ) : (
                  <ul className="space-y-3 sm:space-y-4">
                    <li>
                      <MenuAccountLink
                        to="/auth/login"
                        icon={<LogIn size={18} />}
                        onClick={closeMenu}
                      >
                        {tr('menuLogin')}
                      </MenuAccountLink>
                    </li>
                    <li>
                      <Link
                        to="/auth/register"
                        onClick={closeMenu}
                        className="uppercase text-sm sm:text-[0.95rem] font-semibold tracking-[0.12em] text-ink-500 hover:text-ink-400 transition-colors"
                      >
                        {tr('menuRegister')}
                      </Link>
                    </li>
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function MenuAccountLink({
  to,
  children,
  icon,
  onClick,
}: {
  to: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="flex items-center gap-3 py-2 text-sm uppercase font-semibold tracking-[0.1em] text-ink-400 hover:text-ink-500 transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
