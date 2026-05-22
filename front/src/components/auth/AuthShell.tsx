import { PageContent } from '@/components/layout/PageContent';

const REGISTER_BENEFITS = [
  '«Посмотрю позже» — сохраняйте фильмы в личный список',
  'Оценки 1–10 и история ваших оценок',
  'Отмечайте просмотренное — всё в избранном',
  'Город в профиле — афиша «Новинки» в вашем городе',
] as const;

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
        <div className="max-w-md mx-auto">
          <p className="text-xs uppercase tracking-[0.2em] text-ink-50 mb-2">
            Аккаунт
          </p>
          <h1 className="font-serif text-3xl sm:text-4xl text-ink-500 mb-2">
            {title}
          </h1>
          <p className="text-ink-100 text-sm sm:text-base mb-8">{subtitle}</p>

          {showBenefits && (
            <div className="mb-8 p-4 sm:p-5 bg-site-bg border border-ink-50/12 rounded-sm">
              <p className="text-xs uppercase tracking-wider text-wine-500 font-semibold mb-3">
                Зачем регистрироваться
              </p>
              <ul className="space-y-2 text-sm text-ink-300">
                {REGISTER_BENEFITS.map((line) => (
                  <li key={line} className="flex gap-2">
                    <span className="text-wine-500 shrink-0">—</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-ink-50">
                Сайт можно смотреть без аккаунта — регистрация для личных списков и оценок.
              </p>
            </div>
          )}

          <div className="bg-site-bg border border-ink-50/12 rounded-sm p-6 sm:p-8 shadow-sm">
            {children}
          </div>

          <div className="mt-6 text-center text-sm text-ink-100">{footer}</div>
        </div>
      </PageContent>
    </div>
  );
}
