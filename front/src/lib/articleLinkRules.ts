/**
 * Правила: когда не превращать упоминание в ссылку на /director.
 * Канон для бэка и скриптов: backend/app/article_link_rules.py — при правках синхронизировать.
 */

/** Фамилии/имена, которые часто не про режиссёра в эссе */
export const GLOBAL_SURNAME_DENY = new Set([
  'джонс',
  'миранда',
  'ривз',
  'оппенгеймер',
  'экзюпери',
]);

/** Не линковать персону (по заголовку в БД), если подстрока совпала */
export const GLOBAL_PERSON_TITLE_DENY = [
  'кеану ривз',
  'keanu reeves',
  'тейлор-джой',
  'anya taylor-joy',
  'эдгар райт',
  'edgar wright',
  'антoine de saint-exupery',
  'сент-экзюпери',
  'оппенгеймер',
  'oppenheimer',
];

/** Доп. запреты по slug статьи (упоминание актёра, персонажа, автора) */
export const ARTICLE_PERSON_DENY: Record<string, string[]> = {
  'marvel-fastfud-ili-iskusstvo': [
    'кеану ривз',
    'тейлор-джой',
    'эдгар райт',
  ],
  'secs-v-bolshom-gorode-pochemu-aktualen': ['миранда', 'джонс', 'саманта джонс'],
  'secs-v-bolshom-gorode-do-sih-por': ['миранда', 'джонс', 'саманта джонс'],
  'kino-povernutoe-na-bok': ['сент-экзюпери', 'экзюпери'],
};

export function normalizeForDeny(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, ' ');
}

export function personTitleDenied(slug: string | undefined, title: string): boolean {
  const t = normalizeForDeny(title);
  if (GLOBAL_PERSON_TITLE_DENY.some((d) => t.includes(d) || d.includes(t))) {
    return true;
  }
  if (!slug) return false;
  const perArticle = ARTICLE_PERSON_DENY[slug];
  if (!perArticle) return false;
  return perArticle.some((d) => t.includes(d) || d.includes(t));
}

export function surnameDenied(surname: string): boolean {
  return GLOBAL_SURNAME_DENY.has(normalizeForDeny(surname));
}

/** Диапазоны «…» — названия фильмов/книг, не режиссёры */
export function guillemetRanges(text: string): Array<[number, number]> {
  const ranges: Array<[number, number]> = [];
  let i = 0;
  while (i < text.length) {
    const open = text.indexOf('«', i);
    if (open === -1) break;
    const close = text.indexOf('»', open + 1);
    if (close === -1) break;
    ranges.push([open, close + 1]);
    i = close + 1;
  }
  return ranges;
}

export function isInsideGuillemets(
  start: number,
  end: number,
  ranges: Array<[number, number]>,
): boolean {
  return ranges.some(([a, b]) => start >= a && end <= b);
}
