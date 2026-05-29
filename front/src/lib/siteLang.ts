import { useLocaleStore, type SiteLocale } from '@/stores/locale';

export function getSiteLang(): SiteLocale {
  return useLocaleStore.getState().locale;
}

export function useSiteLang(): SiteLocale {
  return useLocaleStore((s) => s.locale);
}
