/** Убирает эмодзи и лишние пробелы из текста биографии. */
export function stripEmojis(text: string): string {
  return text
    .replace(/\p{Extended_Pictographic}/gu, '')
    .replace(/[\u200d\uFE0F]/g, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const FILMOGRAPHY_SECTION =
  /^(?:\*{0,2}\s*)?(?:основные проекты|главные (?:роли|работы)|фильмография|filmography|main projects|notable (?:works|films)|selected filmography)/i;

const AWARDS_SECTION =
  /^(?:\*{0,2}\s*)?(?:номинации|награды|премии|awards?(?:\s+and\s+nominations)?|nominations?)/i;

const FACT_SECTION =
  /^(?:\*{0,2}\s*)?(?:интересн(?:ый|ая) факт|fun fact|did you know)/i;

/** Секции биографии, которые дублируют блоки ниже на странице. */
function isCutSection(line: string): boolean {
  const t = stripEmojis(line).trim();
  if (!t) return false;
  return (
    FILMOGRAPHY_SECTION.test(t) ||
    AWARDS_SECTION.test(t) ||
    FACT_SECTION.test(t)
  );
}

/** Строка похожа на пункт списка фильмов («Название» (год) …). */
function looksLikeFilmListItem(line: string): boolean {
  const t = stripEmojis(line).trim();
  if (!t || t.length > 220) return false;
  if (/^[-•*·]\s/.test(t)) return true;
  if (/^[«""]/.test(t) && /\(\d{4}\)/.test(t)) return true;
  if (/^[\w«""].{2,60}\s*\(\d{4}\)/.test(t)) return true;
  return false;
}

export interface PersonBioParts {
  lead: string | null;
  body: string | null;
}

/**
 * Готовит биографию для страницы персоны: без смайликов и без перечисления фильмов.
 * Если есть summary — он идёт лидом, description — основной текст (очищенный).
 */
export function buildPersonBio(
  summary: string | null | undefined,
  description: string | null | undefined,
  opts?: { dropAwardsSection?: boolean },
): PersonBioParts {
  const dropAwards = opts?.dropAwardsSection ?? false;
  const raw = (description || summary || '').trim();
  if (!raw) {
    return { lead: summary?.trim() || null, body: null };
  }

  const lines = stripEmojis(raw).split(/\r?\n/);
  const kept: string[] = [];
  let skipBlock = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (!skipBlock && kept.length > 0 && kept[kept.length - 1] !== '') {
        kept.push('');
      }
      continue;
    }

    if (isCutSection(trimmed)) {
      skipBlock =
        FILMOGRAPHY_SECTION.test(stripEmojis(trimmed)) ||
        FACT_SECTION.test(stripEmojis(trimmed)) ||
        (dropAwards && AWARDS_SECTION.test(stripEmojis(trimmed)));
      continue;
    }

    if (skipBlock) {
      if (looksLikeFilmListItem(trimmed)) continue;
      if (/^[A-ZА-ЯЁ]/.test(trimmed) && trimmed.length > 80 && !looksLikeFilmListItem(trimmed)) {
        skipBlock = false;
      } else {
        continue;
      }
    }

    if (looksLikeFilmListItem(trimmed)) continue;

    kept.push(trimmed);
  }

  let body = kept
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  const sum = summary ? stripEmojis(summary.trim()) : null;
  if (sum && body.startsWith(sum)) {
    body = body.slice(sum.length).trim();
  } else if (sum && body) {
    const sumNorm = sum.replace(/\s+/g, ' ');
    const bodyNorm = body.replace(/\s+/g, ' ');
    if (bodyNorm.startsWith(sumNorm)) {
      body = bodyNorm.slice(sumNorm.length).trim();
    }
  }

  const lead = sum && sum !== body ? sum : null;
  return {
    lead: lead || null,
    body: body || null,
  };
}
