/** Фон сайта */
export const SITE_BG = '#E1EFF6';
export const SITE_HOVER_BG = '#97D2FB';

/** Tiffany Blue — как у логотипа FMW */
export const TIFFANY = '#0ABAB5';

/** Акцент английской локали в переключателе языка */
export const LOCALE_EN_ACCENT = '#ECCBD9';

/** Цвета блоков с текстом на карточках статей */
export const ARTICLE_PLATE_COLORS = [
  { bg: '#ECCBD9', textLight: false }, // pale pink
  { bg: '#E1EFF6', textLight: false }, // ice blue
  { bg: '#97D2FB', textLight: false }, // light sky blue
  { bg: '#83BCFF', textLight: false }, // bright sky blue
  { bg: '#0ABAB5', textLight: true }, // teal — светлый текст
] as const;

export function plateColorForIndex(index: number) {
  return ARTICLE_PLATE_COLORS[index % ARTICLE_PLATE_COLORS.length];
}
