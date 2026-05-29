import { Link } from 'react-router-dom';
import { PageContent } from '@/components/layout/PageContent';
import { cn } from '@/lib/utils';

interface ProfileLayoutProps {
  children: React.ReactNode;
  title?: string;
  backTo?: string;
  className?: string;
}

/** Оболочка подстраниц профиля — фон сайта, тёмный текст. */
export function ProfileLayout({
  children,
  title,
  backTo = '/me',
  className,
}: ProfileLayoutProps) {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-site-bg text-ink-500">
      <PageContent className={cn('py-8 sm:py-12', className)}>
        {title && (
          <div className="mb-8 flex items-center gap-4">
            <Link
              to={backTo}
              className="text-sm text-ink-50 hover:text-ink-400 transition-colors"
            >
              ← Профиль
            </Link>
            <h1 className="text-lg sm:text-xl font-semibold tracking-wide text-ink-500">
              {title}
            </h1>
          </div>
        )}
        {children}
      </PageContent>
    </div>
  );
}

interface StatBlockProps {
  label: string;
  value: number;
  to?: string;
  className?: string;
}

export function StatBlock({ label, value, to, className }: StatBlockProps) {
  const inner = (
    <>
      <span className="text-2xl sm:text-3xl font-bold text-ink-500 tabular-nums">
        {value}
      </span>
      <span className="text-xs uppercase tracking-[0.14em] text-ink-50 mt-1">
        {label}
      </span>
    </>
  );

  const boxClass = cn(
    'flex flex-col items-center justify-center rounded-sm bg-cream-50 border border-ink-50/20 p-5 sm:p-6',
    'hover:border-ink-50/40 transition-colors min-h-[100px]',
    className,
  );

  if (to) {
    return (
      <Link to={to} className={boxClass}>
        {inner}
      </Link>
    );
  }

  return <div className={boxClass}>{inner}</div>;
}

/** Высота тела карточки = один ряд из 4 постеров 2:3 (колонки «Избранное» / «Активность»). */
export const PROFILE_TWIN_PANEL_BODY = 'aspect-[8/3] w-full';

export function ProfileSection({
  title,
  action,
  children,
  id,
  className,
  bodyClassName,
  fill,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  id?: string;
  className?: string;
  bodyClassName?: string;
  /** Растянуть секцию на всю высоту ячейки сетки */
  fill?: boolean;
}) {
  return (
    <section
      id={id}
      className={cn(
        'rounded-sm bg-cream-50 border border-ink-50/20 overflow-hidden scroll-mt-32',
        fill && 'h-full flex flex-col',
        className,
      )}
    >
      <div className="flex items-center justify-between px-4 sm:px-5 py-3.5 sm:py-4 border-b border-ink-50/15 shrink-0">
        <h2 className="text-sm sm:text-base lg:text-lg uppercase tracking-[0.16em] sm:tracking-[0.18em] text-ink-300 font-semibold">
          {title}
        </h2>
        {action}
      </div>
      <div
        className={cn(
          'p-4 sm:p-5',
          fill && 'flex-1 flex flex-col min-h-0',
          bodyClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
}
