import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'default' | 'large';
}

/**
 * Логотип «ЛОГО» + три линии над «О» (крупный вариант — как KNMN на kinomania).
 */
export function Logo({ className, size = 'default' }: LogoProps) {
  const isLarge = size === 'large';
  const barColor = 'bg-ink-500';

  return (
    <Link
      to="/"
      className={cn(
        'inline-flex items-end gap-0 font-sans font-black uppercase leading-none select-none text-ink-500',
        isLarge
          ? 'text-[2.25rem] sm:text-5xl lg:text-[3.25rem] tracking-[-0.03em]'
          : 'text-2xl tracking-tight',
        className,
      )}
      aria-label="На главную"
    >
      <span>ЛОГ</span>
      <span className={cn('relative inline-block', isLarge ? 'pb-1' : 'pb-0.5')}>
        <span
          className={cn(
            'absolute left-1/2 -translate-x-1/2 flex flex-col items-center',
            isLarge ? '-top-5 sm:-top-6 gap-1' : '-top-[18px] gap-[3px]',
          )}
          aria-hidden
        >
          <span className={cn('rounded-full', barColor, isLarge ? 'h-[3px] w-7 sm:w-9' : 'h-[2px] w-[22px]')} />
          <span className={cn('rounded-full', barColor, isLarge ? 'h-[3px] w-5 sm:w-7' : 'h-[2px] w-[16px]')} />
          <span className={cn('rounded-full', barColor, isLarge ? 'h-[3px] w-3 sm:w-4' : 'h-[2px] w-[10px]')} />
        </span>
        О
      </span>
    </Link>
  );
}
