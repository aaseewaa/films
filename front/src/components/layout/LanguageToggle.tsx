import { cn } from '@/lib/utils';
import { LOCALE_EN_ACCENT, TIFFANY } from '@/lib/sitePalette';
import { useTranslation } from '@/hooks/useTranslation';
import { useLocaleStore, type SiteLocale } from '@/stores/locale';
import { HEADER_CONTROL_HIT_CLASS, HEADER_LANG_CLASS } from '@/lib/headerNavTheme';

const LOCALE_COLORS: Record<SiteLocale, string> = {
  ru: TIFFANY,
  en: LOCALE_EN_ACCENT,
};

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
        'shrink-0 px-1 lg:px-2 rounded-sm',
        HEADER_CONTROL_HIT_CLASS,
        'hover:opacity-85 active:opacity-75 transition-opacity',
        className,
      )}
      style={{ color: LOCALE_COLORS[locale] }}
      aria-label={locale === 'ru' ? tr('langSwitchToEn') : tr('langSwitchToRu')}
    >
      <span
        className={cn(
          HEADER_LANG_CLASS,
          'uppercase font-semibold tracking-[0.06em] leading-none transition-colors duration-150',
        )}
      >
        {locale}
      </span>
    </button>
  );
}
