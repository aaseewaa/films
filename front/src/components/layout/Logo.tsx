import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  size?: 'default' | 'large';
}

const SIZE_CLASS = {
  large: 'text-[3.8rem] sm:text-[4.8rem] lg:text-[5.7rem]',
  default: 'text-[3.3rem]',
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
