import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  User,
  LogIn,
  LogOut,
  Heart,
  Star,
  History,
} from 'lucide-react';
import { Logo } from './Logo';
import { ExpandableSearch } from './ExpandableSearch';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { to: '/films', label: 'фильмы' },
  { to: '/collections', label: 'коллекции' },
  { to: '/articles', label: 'статьи' },
  { to: '/news', label: 'новинки' },
] as const;

const FULL_MENU_SECTIONS = [
  {
    title: 'Граф режиссёров',
    links: [{ to: '/', label: 'Открыть граф' }],
  },
  {
    title: 'Фильмы',
    links: [{ to: '/films', label: 'Все фильмы' }],
  },
  {
    title: 'Коллекции',
    links: [{ to: '/collections', label: 'Все коллекции' }],
  },
  {
    title: 'Статьи',
    links: [
      { to: '/articles', label: 'Журнал' },
      { to: '/article/hitchcock-arhitektor-trevogi', label: 'Редакция' },
    ],
  },
  {
    title: 'Новинки',
    links: [{ to: '/news', label: 'Афиша проката' }],
  },
  {
    title: 'Поиск',
    links: [{ to: '/search', label: 'Найти фильм или режиссёра' }],
  },
] as const;

/** Высота шапки для calc(100vh - …) на главной */
export const HEADER_HEIGHT_CLASS = 'h-[4.75rem] lg:h-20';

/**
 * Шапка в духе kinomania: белый фон, бургер + крупный логотип слева,
 * крупные пункты меню и лупа справа. Бургер открывает полноэкранное меню.
 */
export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const { isAuthenticated, user, logout } = useAuthStore();

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
      <header className="sticky top-0 z-50 bg-white border-b border-ink-50/12">
        <div
          className={cn(
            'w-full px-4 sm:px-6 lg:px-10 flex items-center justify-between gap-4 lg:gap-8',
            HEADER_HEIGHT_CLASS,
          )}
        >
          <div className="flex items-center gap-3 sm:gap-5 lg:gap-8 min-w-0 flex-1 lg:max-w-[45%]">
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="shrink-0 p-1 -ml-1 text-ink-500 hover:text-ink-400 transition-colors"
              aria-label={menuOpen ? 'Закрыть меню' : 'Открыть меню'}
              aria-expanded={menuOpen}
            >
              {menuOpen ? (
                <X size={28} strokeWidth={1.75} />
              ) : (
                <Menu size={28} strokeWidth={1.75} />
              )}
            </button>
            <Logo size="large" className="truncate" />
          </div>

          <div className="hidden md:flex items-center justify-end flex-1 min-w-0 gap-3 lg:gap-4">
            <nav
              className={cn(
                'flex items-center justify-end flex-wrap gap-x-6 lg:gap-x-10 xl:gap-x-14 gap-y-1',
                'transition-transform duration-300 ease-out',
                searchExpanded && '-translate-x-1',
              )}
              aria-label="Основное меню"
            >
              {NAV_ITEMS.map(({ to, label }) => {
                const active =
                  location.pathname === to ||
                  location.pathname.startsWith(`${to}/`);
                return (
                  <Link
                    key={to}
                    to={to}
                    className={cn(
                      'uppercase font-semibold tracking-[0.06em] whitespace-nowrap',
                      'text-[0.95rem] lg:text-[1.05rem] xl:text-lg',
                      'transition-colors hover:text-ink-400',
                      active ? 'text-ink-500' : 'text-ink-300',
                    )}
                  >
                    {label}
                  </Link>
                );
              })}
            </nav>

            <ExpandableSearch onExpandedChange={setSearchExpanded} />
          </div>

          <button
            type="button"
            onClick={() => navigate('/search')}
            className="md:hidden shrink-0 p-1 text-ink-500 hover:text-ink-400 transition-colors"
            aria-label="Поиск"
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
      </header>

      {menuOpen && (
        <div
          className="fixed inset-x-0 bottom-0 z-40 bg-white overflow-y-auto top-[4.75rem] lg:top-20"
          role="dialog"
          aria-modal="true"
          aria-label="Меню сайта"
        >
          <div className="px-6 sm:px-10 lg:px-16 xl:px-20 py-10 sm:py-12 lg:py-16 min-h-full flex flex-col">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-10 gap-y-12 lg:gap-y-16 flex-1 max-w-6xl">
              {FULL_MENU_SECTIONS.map((section) => (
                <div key={section.title}>
                  <h2 className="font-sans text-3xl sm:text-4xl lg:text-[2.5rem] font-bold leading-tight text-[#6d7a6f] mb-5 sm:mb-6">
                    {section.title}
                  </h2>
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
            </div>

            <div className="mt-12 lg:mt-16 pt-8 border-t border-ink-50/12 max-w-6xl">
              {isAuthenticated && user ? (
                <>
                  <p className="text-xs uppercase tracking-[0.2em] text-ink-50 mb-4">
                    {user.display_name}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <MenuAccountLink to="/me" icon={<User size={18} />} onClick={closeMenu}>
                      Профиль
                    </MenuAccountLink>
                    <MenuAccountLink
                      to="/me/favorites"
                      icon={<Heart size={18} />}
                      onClick={closeMenu}
                    >
                      Избранное
                    </MenuAccountLink>
                    <MenuAccountLink
                      to="/me/ratings"
                      icon={<Star size={18} />}
                      onClick={closeMenu}
                    >
                      Оценки
                    </MenuAccountLink>
                    <MenuAccountLink
                      to="/me/history"
                      icon={<History size={18} />}
                      onClick={closeMenu}
                    >
                      История
                    </MenuAccountLink>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      closeMenu();
                    }}
                    className="mt-4 flex items-center gap-3 text-sm uppercase tracking-[0.12em] font-semibold text-ink-300 hover:text-ink-500"
                  >
                    <LogOut size={18} />
                    Выйти
                  </button>
                </>
              ) : (
                <div className="flex flex-wrap gap-6">
                  <MenuAccountLink to="/auth/login" icon={<LogIn size={18} />} onClick={closeMenu}>
                    Войти
                  </MenuAccountLink>
                  <Link
                    to="/auth/register"
                    onClick={closeMenu}
                    className="uppercase text-sm font-semibold tracking-[0.12em] text-ink-500 hover:text-ink-400"
                  >
                    Регистрация
                  </Link>
                </div>
              )}
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
