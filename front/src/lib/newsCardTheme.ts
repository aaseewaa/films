/** Палитра карточек «как в журнале» для афиши и новостей-заглушек */
export interface NewsCardTheme {
  bg: string;
  textLight: boolean;
}

const THEMES: NewsCardTheme[] = [
  { bg: '#d4e157', textLight: false },
  { bg: '#9ccc65', textLight: false },
  { bg: '#1e3a5f', textLight: true },
  { bg: '#e8e6e1', textLight: false },
  { bg: '#C1121F', textLight: true },
  { bg: '#2D6A4F', textLight: true },
  { bg: '#4895EF', textLight: true },
  { bg: '#5A189A', textLight: true },
];

export function themeForIndex(index: number): NewsCardTheme {
  return THEMES[index % THEMES.length];
}
