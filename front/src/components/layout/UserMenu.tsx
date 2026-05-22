import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, User, Heart, Star, History, LogIn, LogOut, BookOpen, Layers, Film, Newspaper } from 'lucide-react';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

/**
 * Главное навигационное меню. Открывается с правой стороны хедера.
 * Включает: каталог разделов + личный кабинет если авторизован.
 */
export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { isAuthenticated, user, logout } = useAuthStore();

  // Закрываем при клике вне меню
  useEffect(() => {
    if (!isOpen) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [isOpen]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-2 h-10 px-3 rounded-sm text-ink-300 hover:bg-site-hover transition-colors"
        aria-label="Меню"
      >
        <Menu size={18} />
        <span className="text-sm">Меню</span>
      </button>

      {isOpen && (
        <div
          className={cn(
            'absolute right-0 top-full mt-2 w-72',
            'bg-site-bg border border-ink-50/15 rounded-sm shadow-lg',
            'animate-slide-up z-50'
          )}
        >
          {/* Разделы сайта */}
          <div className="p-2">
            <div className="px-3 py-2 text-xs uppercase tracking-wider text-ink-50 font-medium">
              Разделы
            </div>
            <MenuLink to="/" icon={<Layers size={16} />} onClick={() => setIsOpen(false)}>
              Граф режиссёров
            </MenuLink>
            <MenuLink to="/films" icon={<Film size={16} />} onClick={() => setIsOpen(false)}>
              Все фильмы
            </MenuLink>
            <MenuLink to="/collections" icon={<Layers size={16} />} onClick={() => setIsOpen(false)}>
              Коллекции
            </MenuLink>
            <MenuLink to="/articles" icon={<BookOpen size={16} />} onClick={() => setIsOpen(false)}>
              Журнал
            </MenuLink>
            <MenuLink to="/news" icon={<Newspaper size={16} />} onClick={() => setIsOpen(false)}>
              Новинки
            </MenuLink>
          </div>

          <div className="divider-thin" />

          {/* Аккаунт */}
          <div className="p-2">
            {isAuthenticated && user ? (
              <>
                <div className="px-3 py-2 text-xs uppercase tracking-wider text-ink-50 font-medium">
                  {user.display_name}
                </div>
                <MenuLink to="/me" icon={<User size={16} />} onClick={() => setIsOpen(false)}>
                  Профиль
                </MenuLink>
                <MenuLink to="/me/favorites" icon={<Heart size={16} />} onClick={() => setIsOpen(false)}>
                  Избранное
                </MenuLink>
                <MenuLink to="/me/ratings" icon={<Star size={16} />} onClick={() => setIsOpen(false)}>
                  Мои оценки
                </MenuLink>
                <MenuLink to="/me/history" icon={<History size={16} />} onClick={() => setIsOpen(false)}>
                  История
                </MenuLink>
                <button
                  onClick={() => { logout(); setIsOpen(false); }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-ink-300 hover:bg-site-hover rounded-sm transition-colors"
                >
                  <LogOut size={16} />
                  Выйти
                </button>
              </>
            ) : (
              <>
                <MenuLink to="/auth/login" icon={<LogIn size={16} />} onClick={() => setIsOpen(false)}>
                  Войти
                </MenuLink>
                <MenuLink to="/auth/register" onClick={() => setIsOpen(false)}>
                  Регистрация
                </MenuLink>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface MenuLinkProps {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick?: () => void;
}

function MenuLink({ to, icon, children, onClick }: MenuLinkProps) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="flex items-center gap-3 px-3 py-2 text-sm text-ink-300 hover:bg-site-hover rounded-sm transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
