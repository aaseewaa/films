import type { ArticleSummary } from '@/api/types';
import { t, type UiKey } from '@/lib/i18n';
import { getSiteLang } from '@/lib/siteLang';
import { plateColorForIndex } from '@/lib/sitePalette';
import type { SiteLocale } from '@/stores/locale';

export type ArticleCardVariant = 'stack' | 'overlay' | 'compact';

export interface ArticleTheme {
  slug: string;
  bg: string;
  textLight: boolean;
  /** 1 или 2 из 3 колонок */
  colSpan: 1 | 2;
  variant: ArticleCardVariant;
  authorName?: string;
}

/** Порядок и раскладка карточек журнала (статьи из БД) */
const THEMES: Omit<ArticleTheme, 'bg' | 'textLight'>[] = [
  {
    slug: 'kino-poslednih-5-let-upadnichestvo',
    colSpan: 2,
    variant: 'stack',
    authorName: 'Редакция FilmCine',
  },
  {
    slug: 'secs-v-bolshom-gorode-pochemu-aktualen',
    colSpan: 1,
    variant: 'stack',
  },
  {
    slug: 'kino-povernutoe-na-bok',
    colSpan: 1,
    variant: 'compact',
  },
  {
    slug: 'klan-koppola',
    colSpan: 1,
    variant: 'stack',
  },
  {
    slug: 'novye-lica-golivuda',
    colSpan: 1,
    variant: 'overlay',
  },
  {
    slug: 'kino-eto-iskusstvo',
    colSpan: 2,
    variant: 'compact',
  },
  {
    slug: 'ave-mariya-toska-po-horoshemu-koncu',
    colSpan: 1,
    variant: 'stack',
  },
  {
    slug: 'marvel-fastfud-ili-iskusstvo',
    colSpan: 1,
    variant: 'compact',
  },
  {
    slug: 'elena-prekrasnaya-tsvet-kozhi',
    colSpan: 1,
    variant: 'compact',
  },
  {
    slug: 'kanny-bez-illyuziy',
    colSpan: 1,
    variant: 'overlay',
  },
];

const THEMES_WITH_COLORS: ArticleTheme[] = THEMES.map((theme, index) => {
  const { bg, textLight } = plateColorForIndex(index);
  return { ...theme, bg, textLight };
});

const TYPE_KEYS: Record<string, UiKey> = {
  essay: 'articleTypeEssay',
  review: 'articleTypeReview',
  analysis: 'articleTypeAnalysis',
  interview: 'articleTypeInterview',
  editorial: 'articleTypeEditorial',
  roundtable: 'articleTypeRoundtable',
};

export function articleTypeLabel(type: string, locale: SiteLocale = getSiteLang()): string {
  const key = type.toLowerCase();
  const uiKey = TYPE_KEYS[key];
  return uiKey ? t(locale, uiKey) : type;
}

export function formatArticleDate(
  iso: string | null | undefined,
  locale: SiteLocale = getSiteLang(),
): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale === 'en' ? 'en-US' : 'ru-RU', {
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
  const found = THEMES_WITH_COLORS.find((t) => t.slug === slug);
  if (found) return found;

  const { bg, textLight } = plateColorForIndex(slug.length);
  return {
    slug,
    bg,
    textLight,
    colSpan: 1,
    variant: 'stack',
  };
}

export function authorForArticle(
  article: ArticleSummary,
  theme: ArticleTheme,
  locale: SiteLocale = getSiteLang(),
): string {
  if (theme.authorName) return theme.authorName;
  if (article.main_subject?.title) {
    const title = article.main_subject.title;
    return title.startsWith('О ') || title.startsWith('о ') ? title.slice(2) : title;
  }
  return t(locale, 'authorEditorial');
}

export function orderArticlesForJournal(items: ArticleSummary[]): ArticleSummary[] {
  const bySlug = new Map(items.map((a) => [a.slug, a]));
  const ordered: ArticleSummary[] = [];
  const used = new Set<number>();

  for (const t of THEMES_WITH_COLORS) {
    const a = bySlug.get(t.slug);
    if (a) {
      ordered.push(a);
      used.add(a.id);
    }
  }

  const rest = items
    .filter((a) => !used.has(a.id))
    .sort((a, b) => {
      const ta = a.published_at ? Date.parse(a.published_at) : 0;
      const tb = b.published_at ? Date.parse(b.published_at) : 0;
      if (tb !== ta) return tb - ta;
      return b.id - a.id;
    });

  return [...ordered, ...rest];
}
