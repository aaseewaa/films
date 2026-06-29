import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'default' | 'large';
}

const SIZE_CLASS = {
  large: 'text-[2.5rem] sm:text-[3rem] lg:text-[3.35rem] xl:text-[4rem] 2xl:text-[5.7rem]',
  default: 'text-[2.5rem] sm:text-[2.85rem]',
} as const;

/** Логотип FMW — один слой Pluffy Loon Outline Shadow (как заголовки каталога) */
export function Logo({ className, size = 'default' }: LogoProps) {
  const isLarge = size === 'large';
  const textClass = cn(SIZE_CLASS[isLarge ? 'large' : 'default'], className);

  return (
    <Link
      to="/"
      className={cn('inline-flex items-center select-none hover:no-underline', textClass)}
      aria-label="На главную"
    >
      <span className="logo-fmw text-tiffany uppercase leading-none whitespace-nowrap">FMW</span>
    </Link>
  );
}
