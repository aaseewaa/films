import { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, User, LogIn, LogOut, Heart, Star, History } from 'lucide-react';
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

/** Высота шапки для calc(100vh - …) на главной */
export const HEADER_HEIGHT_CLASS = 'h-[4.75rem] lg:h-20';

/**
 * Шапка в духе kinomania: белый фон, бургер + крупный логотип слева,
 * крупные пункты меню и лупа справа, на всю ширину.
 */
export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const { isAuthenticated, user, logout } = useAuthStore();

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setDrawerOpen(false);
    }
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [drawerOpen]);

  return (
    <>
      <header className="sticky top-0 z-40 bg-white border-b border-ink-50/12">
        <div
          className={cn(
            'w-full px-4 sm:px-6 lg:px-10 flex items-center justify-between gap-4 lg:gap-8',
            HEADER_HEIGHT_CLASS,
          )}
        >
          {/* Слева: бургер + логотип — занимают левую половину на десктопе */}
          <div className="flex items-center gap-3 sm:gap-5 lg:gap-8 min-w-0 flex-1 lg:max-w-[45%]">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="shrink-0 p-1 -ml-1 text-ink-500 hover:text-ink-400 transition-colors"
              aria-label="Открыть меню"
            >
              <Menu size={28} strokeWidth={1.75} />
            </button>
            <Logo size="large" className="truncate" />
          </div>

          {/* Справа: навигация + поиск */}
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
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20 16 16" />
            </svg>
          </button>
        </div>
      </header>

      {/* Выезжающее меню (бургер) */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex">
          <button
            type="button"
            className="flex-1 bg-ink-500/40"
            aria-label="Закрыть меню"
            onClick={() => setDrawerOpen(false)}
          />
          <aside
            ref={drawerRef}
            className="w-[min(100%,320px)] bg-white shadow-xl flex flex-col animate-slide-up"
          >
            <div className="flex items-center justify-between px-5 h-[4.75rem] border-b border-ink-50/12">
              <Logo size="default" />
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="p-1 text-ink-300 hover:text-ink-500"
                aria-label="Закрыть"
              >
                <X size={24} />
              </button>
            </div>

            <nav className="flex flex-col p-4 gap-1">
              <DrawerLink to="/" onClick={() => setDrawerOpen(false)}>
                Граф режиссёров
              </DrawerLink>
              {NAV_ITEMS.map(({ to, label }) => (
                <DrawerLink key={to} to={to} onClick={() => setDrawerOpen(false)}>
                  {label}
                </DrawerLink>
              ))}
              <DrawerLink to="/search" onClick={() => setDrawerOpen(false)}>
                Поиск
              </DrawerLink>
            </nav>

            <div className="mt-auto p-4 border-t border-ink-50/12 space-y-1">
              {isAuthenticated && user ? (
                <>
                  <p className="px-3 py-2 text-xs uppercase tracking-wider text-ink-50">
                    {user.display_name}
                  </p>
                  <DrawerLink to="/me" icon={<User size={18} />} onClick={() => setDrawerOpen(false)}>
                    Профиль
                  </DrawerLink>
                  <DrawerLink to="/me/favorites" icon={<Heart size={18} />} onClick={() => setDrawerOpen(false)}>
                    Избранное
                  </DrawerLink>
                  <DrawerLink to="/me/ratings" icon={<Star size={18} />} onClick={() => setDrawerOpen(false)}>
                    Оценки
                  </DrawerLink>
                  <DrawerLink to="/me/history" icon={<History size={18} />} onClick={() => setDrawerOpen(false)}>
                    История
                  </DrawerLink>
                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setDrawerOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-3 py-3 text-base text-ink-300 hover:bg-ink-50/8 rounded-sm"
                  >
                    <LogOut size={18} />
                    Выйти
                  </button>
                </>
              ) : (
                <DrawerLink to="/auth/login" icon={<LogIn size={18} />} onClick={() => setDrawerOpen(false)}>
                  Войти
                </DrawerLink>
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}

function DrawerLink({
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
      className="flex items-center gap-3 px-3 py-3 text-lg uppercase font-semibold tracking-wide text-ink-400 hover:bg-ink-50/8 rounded-sm transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
