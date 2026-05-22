import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { queryClient } from '@/lib/queryClient';

export type SiteLocale = 'ru' | 'en';

interface LocaleState {
  locale: SiteLocale;
  toggleLocale: () => void;
  setLocale: (locale: SiteLocale) => void;
}

function afterLocaleChange() {
  void queryClient.invalidateQueries();
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: 'ru',
      toggleLocale: () =>
        set((s) => {
          const locale = s.locale === 'ru' ? 'en' : 'ru';
          afterLocaleChange();
          return { locale };
        }),
      setLocale: (locale) =>
        set((s) => {
          if (s.locale === locale) return s;
          afterLocaleChange();
          return { locale };
        }),
    }),
    { name: 'filmcine-locale' },
  ),
);
