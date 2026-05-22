import { t, type UiKey } from '@/lib/i18n';
import { useSiteLang } from '@/lib/siteLang';

export function useTranslation() {
  const locale = useSiteLang();
  return (key: UiKey) => t(locale, key);
}
