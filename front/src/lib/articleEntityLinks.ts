import type { ArticleEntityRef } from '@/api/types';
import {
  guillemetRanges,
  isInsideGuillemets,
  personTitleDenied,
  surnameDenied,
} from '@/lib/articleLinkRules';

export type ArticleTextSegment =
  | { kind: 'text'; value: string }
  | { kind: 'person'; value: string; personId: number };

/** Минимальная длина фамилии для отдельного совпадения */
const MIN_SURNAME_LENGTH = 4;

const MIN_FULL_NAME_LENGTH = 4;

const LETTER = '\\p{L}';
const BOUNDARY_BEFORE = `(?<![${LETTER}\\p{N}_])`;
const BOUNDARY_AFTER = `(?![${LETTER}\\p{N}_])`;

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function startsWithCapital(s: string): boolean {
  return /^[A-ZА-ЯЁ]/.test(s);
}

function overlaps(
  start: number,
  end: number,
  occupied: Array<[number, number]>,
): boolean {
  return occupied.some(([s, e]) => start < e && end > s);
}

function surnameFromTitle(title: string): string | null {
  const parts = title.trim().split(/\s+/);
  if (parts.length < 2) return null;
  const last = parts[parts.length - 1];
  if (last.length < MIN_SURNAME_LENGTH || !startsWithCapital(last)) return null;
  if (surnameDenied(last)) return null;
  return last;
}

function regexForName(name: string): RegExp | null {
  const term = name.trim();
  if (term.length < MIN_FULL_NAME_LENGTH || !startsWithCapital(term)) return null;
  return new RegExp(
    `${BOUNDARY_BEFORE}${escapeRegExp(term)}${BOUNDARY_AFTER}`,
    'gu',
  );
}

function patternsForPerson(
  ref: ArticleEntityRef,
  articleSlug?: string,
): { personId: number; re: RegExp }[] {
  const full = ref.title?.trim();
  if (!full || personTitleDenied(articleSlug, full)) return [];

  const out: { personId: number; re: RegExp }[] = [];
  const fullRe = regexForName(full);
  if (fullRe) out.push({ personId: ref.entity_id, re: fullRe });

  const surname = surnameFromTitle(full);
  if (surname) {
    const surnameRe = regexForName(surname);
    if (surnameRe) out.push({ personId: ref.entity_id, re: surnameRe });
  }
  return out;
}

function isValidMatch(
  text: string,
  start: number,
  end: number,
  quoteRanges: Array<[number, number]>,
): boolean {
  const slice = text.slice(start, end);
  if (!startsWithCapital(slice)) return false;
  if (isInsideGuillemets(start, end, quoteRanges)) return false;
  const before = start > 0 ? text[start - 1] : '';
  const after = end < text.length ? text[end] : '';
  if (before && /[\p{L}\p{N}_]/u.test(before)) return false;
  if (after && /[\p{L}\p{N}_]/u.test(after)) return false;
  return true;
}

/** Упоминания режиссёров: целое слово с заглавной, не в «кавычках», не из deny-листа. */
export function splitArticleTextWithPersonLinks(
  text: string,
  relatedEntities: ArticleEntityRef[],
  articleSlug?: string,
): ArticleTextSegment[] {
  const persons = relatedEntities.filter(
    (r) => r.entity_type === 'person' && !personTitleDenied(articleSlug, r.title),
  );
  if (!text || persons.length === 0) {
    return [{ kind: 'text', value: text }];
  }

  const quoteRanges = guillemetRanges(text);
  const patterns: { personId: number; re: RegExp }[] = [];
  const seen = new Set<string>();
  for (const ref of persons) {
    for (const p of patternsForPerson(ref, articleSlug)) {
      const key = `${p.personId}:${p.re.source}`;
      if (seen.has(key)) continue;
      seen.add(key);
      patterns.push(p);
    }
  }

  const occupied: Array<[number, number]> = [];
  const matches: Array<{ start: number; end: number; personId: number; value: string }> = [];

  for (const { personId, re } of patterns) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const start = m.index;
      const end = start + m[0].length;
      if (!isValidMatch(text, start, end, quoteRanges)) continue;
      if (overlaps(start, end, occupied)) continue;
      matches.push({ start, end, personId, value: m[0] });
      occupied.push([start, end]);
    }
  }

  if (matches.length === 0) {
    return [{ kind: 'text', value: text }];
  }

  matches.sort((a, b) => a.start - b.start);

  const out: ArticleTextSegment[] = [];
  let cursor = 0;
  for (const hit of matches) {
    if (hit.start > cursor) {
      out.push({ kind: 'text', value: text.slice(cursor, hit.start) });
    }
    out.push({ kind: 'person', value: hit.value, personId: hit.personId });
    cursor = hit.end;
  }
  if (cursor < text.length) {
    out.push({ kind: 'text', value: text.slice(cursor) });
  }
  return out;
}
