const ROLE_LABELS: Record<string, string> = {
  director: 'Режиссёр',
  writer: 'Сценарист',
  actor: 'Актёр',
  producer: 'Продюсер',
  cinematographer: 'Оператор',
  composer: 'Композитор',
  editor: 'Монтажёр',
  production_designer: 'Художник-постановщик',
  costume_designer: 'Художник по костюмам',
  voice_actor: 'Озвучка',
};

const ROLE_ORDER = [
  'director',
  'writer',
  'producer',
  'actor',
  'cinematographer',
  'composer',
  'editor',
  'production_designer',
  'costume_designer',
  'voice_actor',
] as const;

/** Список ролей персоны для шапки (из film_person или флагов is_director/is_actor). */
export function formatPersonRoles(person: {
  is_director?: boolean;
  is_actor?: boolean;
  crew_roles?: string[] | null;
}): string | null {
  const fromDb = new Set(person.crew_roles ?? []);
  if (person.is_director) fromDb.add('director');
  if (person.is_actor) fromDb.add('actor');

  const labels = ROLE_ORDER.filter((r) => fromDb.has(r)).map((r) => ROLE_LABELS[r]);
  return labels.length > 0 ? labels.join(', ') : null;
}
