import { plateColorForIndex } from '@/lib/sitePalette';

export interface NewsCardTheme {
  bg: string;
  textLight: boolean;
}

export function themeForIndex(index: number): NewsCardTheme {
  return plateColorForIndex(index);
}
