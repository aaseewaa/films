/** Главная с графом — без боковых полей контейнера. */
export function isGraphPage(pathname: string): boolean {
  return pathname === '/';
}

/** Класс центральной колонки: поля max(1.25rem, 6vw) слева и справа (~88% контента). */
export const SITE_GUTTER_CLASS = 'page-content';
