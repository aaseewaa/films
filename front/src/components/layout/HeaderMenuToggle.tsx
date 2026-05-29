import { cn } from '@/lib/utils';

/** Высота совпадает с крупным логотипом FMW в шапке */
const TOGGLE_SIZE_CLASS = 'h-[3.8rem] sm:h-[4.8rem] lg:h-[5.7rem]';
const BAR_CLASS =
  'absolute left-0 right-0 rounded-full bg-current transition-all duration-300 ease-out h-[0.38rem] sm:h-[0.46rem] lg:h-[0.54rem]';

interface HeaderMenuToggleProps {
  open: boolean;
  onClick: () => void;
}

/** Три полоски → крестик; размер как у логотипа */
export function HeaderMenuToggle({ open, onClick }: HeaderMenuToggleProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'shrink-0 relative inline-flex items-center justify-center',
        TOGGLE_SIZE_CLASS,
        'w-[2.85rem] sm:w-[3.5rem] lg:w-[4.15rem]',
        'rounded-sm text-ink-500 hover:text-ink-400 hover:bg-site-hover transition-colors',
      )}
      aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
      aria-expanded={open}
    >
      <span className="relative block w-full h-[52%]" aria-hidden>
        <span
          className={cn(BAR_CLASS, 'top-0', open && 'top-1/2 -translate-y-1/2 rotate-45')}
        />
        <span
          className={cn(
            BAR_CLASS,
            'top-1/2 -translate-y-1/2',
            open && 'opacity-0 scale-x-0',
          )}
        />
        <span
          className={cn(
            BAR_CLASS,
            'bottom-0',
            open && 'bottom-1/2 translate-y-1/2 -rotate-45',
          )}
        />
      </span>
    </button>
  );
}
