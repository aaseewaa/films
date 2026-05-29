import { useEffect } from 'react';
import { useSiteLang } from '@/lib/siteLang';

/** Синхронизирует `<html lang>` с выбранной локалью. */
export function LocaleSync() {
  const locale = useSiteLang();

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  return null;
}
