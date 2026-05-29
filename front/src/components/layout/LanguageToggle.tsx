import { cn } from '@/lib/utils';
import { LOCALE_EN_ACCENT, TIFFANY } from '@/lib/sitePalette';
import { useTranslation } from '@/hooks/useTranslation';
import { useLocaleStore, type SiteLocale } from '@/stores/locale';

const LOCALE_COLORS: Record<SiteLocale, string> = {
  ru: TIFFANY,
  en: LOCALE_EN_ACCENT,
};

const LABEL_CLASS =
  'uppercase font-semibold tracking-[0.06em] text-[1.6rem] lg:text-[1.95rem] xl:text-[2.25rem] leading-none transition-colors duration-150';

/**
 * Переключатель языка: показывает ru (Tiffany) или en (#ECCBD9), по клику меняет.
 */
export function LanguageToggle({ className }: { className?: string }) {
  const locale = useLocaleStore((s) => s.locale);
  const toggleLocale = useLocaleStore((s) => s.toggleLocale);
  const tr = useTranslation();

  return (
    <button
      type="button"
      onClick={toggleLocale}
      className={cn(
        'shrink-0 px-2.5 lg:px-3.5 py-1.5 rounded-sm',
        'hover:opacity-85 active:opacity-75 transition-opacity',
        className,
      )}
      style={{ color: LOCALE_COLORS[locale] }}
      aria-label={locale === 'ru' ? tr('langSwitchToEn') : tr('langSwitchToRu')}
    >
      <span className={LABEL_CLASS}>{locale}</span>
    </button>
  );
}
