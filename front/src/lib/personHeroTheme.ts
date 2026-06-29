/** Плашки текстовой части шапки персоны (режиссёр / актёр). */
export const PERSON_HERO_PLATES = [
  {
    id: 'cream',
    bg: '#FFEEDD',
    textLight: false,
  },
  {
    id: 'blush',
    bg: '#ECCBD9',
    textLight: false,
  },
  {
    id: 'aqua',
    bg: '#0ABAB5',
    textLight: true,
  },
  {
    id: 'sage',
    bg: '#60746d',
    textLight: true,
  },
] as const;

export type PersonHeroPlate = (typeof PERSON_HERO_PLATES)[number];

/**
 * Стабильный цвет для карточки: id персоны + «половина» биографии
 * (короткая / длинная), чтобы палитра распределялась ровнее, но не менялась при перезагрузке.
 */
export function personHeroPlate(person: {
  id: number;
  summary?: string | null;
  description?: string | null;
}): PersonHeroPlate {
  const bioLen = (person.summary?.length ?? 0) + (person.description?.length ?? 0);
  const longBio = bioLen > 420;
  const idx = (person.id + (longBio ? 2 : 0)) % PERSON_HERO_PLATES.length;
  return PERSON_HERO_PLATES[idx]!;
}

/** Та же логика палитры, что у режиссёра: id + «длина» профиля. */
export function profileHeroPlate(user: {
  id: number;
  display_name?: string | null;
  email?: string | null;
  city?: string | null;
}): PersonHeroPlate {
  return personHeroPlate({
    id: user.id,
    summary: user.display_name,
    description: [user.email, user.city].filter(Boolean).join(' · ') || null,
  });
}
