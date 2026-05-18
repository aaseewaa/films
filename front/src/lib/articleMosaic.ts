import type { ArticleSummary } from '@/api/types';

export interface ArticleTheme {
  slug: string;
  bg: string;
  textLight: boolean;
  /** 1 = узкая колонка, 2 = широкая (2 из 4) */
  colSpan: 1 | 2;
}

/**
 * Сетка 4 колонки (как на макете):
 * Ряд 1: [1 Хичкок ×2][2 Кубрик][3 Тарковский]
 * Ряд 2: [4 Бергман][6 Соррентино][5 Линч ×2]
 * Ряд 3: [7 Тарантино] …
 */
const THEMES: ArticleTheme[] = [
  {
    slug: 'hitchcock-arhitektor-trevogi',
    bg: '#C1121F',
    textLight: true,
    colSpan: 2,
  },
  {
    slug: 'kubrick-vremya-kak-material',
    bg: '#2D6A4F',
    textLight: true,
    colSpan: 1,
  },
  {
    slug: 'tarkovsky-poeziya-peizaja',
    bg: '#E9C46A',
    textLight: false,
    colSpan: 1,
  },
  {
    slug: 'bergman-lico-kak-peizaj',
    bg: '#4895EF',
    textLight: true,
    colSpan: 1,
  },
  {
    slug: 'sorrentino-barokko-sovremennosti',
    bg: '#70E000',
    textLight: false,
    colSpan: 1,
  },
  {
    slug: 'lynch-zvuk-kak-geroi',
    bg: '#5A189A',
    textLight: true,
    colSpan: 2,
  },
  {
    slug: 'tarantino-kinokukhnya-i-nasilie',
    bg: '#FF5400',
    textLight: true,
    colSpan: 1,
  },
];

const TYPE_LABELS: Record<string, string> = {
  essay: 'ЭССЕ',
  review: 'РЕЦЕНЗИЯ',
  analysis: 'АНАЛИЗ',
  interview: 'ИНТЕРВЬЮ',
  editorial: 'РЕДАКЦИЯ',
};

export function articleTypeLabel(type: string): string {
  return TYPE_LABELS[type.toLowerCase()] ?? type.toUpperCase();
}

export function formatArticleDate(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return '';
  }
}

export function resolveImage(article: ArticleSummary): string | null {
  return (
    article.cover_image ||
    article.main_subject?.images?.primary ||
    article.main_subject?.images?.thumbnail ||
    null
  );
}

export function themeForSlug(slug: string): ArticleTheme {
  return (
    THEMES.find((t) => t.slug === slug) ?? {
      slug,
      bg: '#FFBE0B',
      textLight: false,
      colSpan: 1,
    }
  );
}

export function orderArticlesForJournal(items: ArticleSummary[]): ArticleSummary[] {
  const bySlug = new Map(items.map((a) => [a.slug, a]));
  const ordered: ArticleSummary[] = [];
  for (const t of THEMES) {
    const a = bySlug.get(t.slug);
    if (a) ordered.push(a);
  }
  for (const a of items) {
    if (!ordered.some((x) => x.id === a.id)) ordered.push(a);
  }
  return ordered;
}
