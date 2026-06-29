import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { PageContent } from '@/components/layout/PageContent';
import { cn } from '@/lib/utils';

const REGISTER_BENEFITS = [
  '«Посмотрю позже» — сохраняйте фильмы в личный список',
  'Оценки 1–10 и история ваших оценок',
  'Отмечайте просмотренное — всё в избранном',
  'Город в профиле — афиша «Новинки» в вашем городе',
] as const;

function RegisterBenefits() {
  const [open, setOpen] = useState(false);

  return (
    <div className="mb-6 p-4 sm:p-5 bg-site-bg border border-ink-50/12 rounded-sm">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className={cn(
          'flex w-full items-center justify-between gap-4 text-left',
          'font-serif text-2xl sm:text-3xl uppercase tracking-wide text-tiffany font-semibold',
          'cursor-pointer transition-colors hover:text-tiffany-dark',
        )}
      >
        <span>Зачем регистрироваться</span>
        <ChevronDown
          size={28}
          strokeWidth={2}
          className={cn('shrink-0 transition-transform duration-200', open && 'rotate-180')}
          aria-hidden
        />
      </button>

      {open && (
        <div className="mt-4">
          <ul className="space-y-3 text-base sm:text-lg text-ink-300 leading-relaxed">
            {REGISTER_BENEFITS.map((line) => (
              <li key={line} className="flex gap-3">
                <span className="text-tiffany shrink-0">—</span>
                <span>{line}</span>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-sm sm:text-base text-ink-50 leading-relaxed">
            Сайт можно смотреть без аккаунта — регистрация для личных списков и оценок.
          </p>
        </div>
      )}
    </div>
  );
}

interface AuthShellProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
  showBenefits?: boolean;
}

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  showBenefits = false,
}: AuthShellProps) {
  return (
    <div className="bg-site-bg min-h-[calc(100vh-5.75rem)] sm:min-h-[calc(100vh-6rem)] lg:min-h-[calc(100vh-6.5rem)]">
      <PageContent className="py-12 sm:py-16">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-50 mb-3">
          Аккаунт
        </p>

        <div className="w-full max-w-[64rem] mx-auto">
          <div className="px-5 sm:px-6 text-left mb-6">
            <h1 className="font-serif text-4xl sm:text-5xl text-ink-500 mb-2">
              {title}
            </h1>
            <p className="text-ink-100 text-base sm:text-lg leading-snug">{subtitle}</p>
          </div>

          {showBenefits && <RegisterBenefits />}

          <div className="bg-site-bg border border-ink-50/12 rounded-sm p-6 sm:p-7 shadow-sm text-left">
            {children}
          </div>

          <div className="mt-6 text-center text-xl sm:text-2xl text-ink-100">{footer}</div>
        </div>
      </PageContent>
    </div>
  );
}
