import { t, type UiKey } from '@/lib/i18n';
import { getSiteLang } from '@/lib/siteLang';
import type { SiteLocale } from '@/stores/locale';

const ROLE_KEYS: Record<string, UiKey> = {
  director: 'roleDirector',
  writer: 'roleWriter',
  actor: 'roleActor',
  producer: 'roleProducer',
  cinematographer: 'roleCinematographer',
  composer: 'roleComposer',
  editor: 'roleEditor',
  production_designer: 'roleProductionDesigner',
  costume_designer: 'roleCostumeDesigner',
  voice_actor: 'roleVoiceActor',
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
export function formatPersonRoles(
  person: {
    is_director?: boolean;
    is_actor?: boolean;
    crew_roles?: string[] | null;
  },
  locale: SiteLocale = getSiteLang(),
): string | null {
  const fromDb = new Set(person.crew_roles ?? []);
  if (person.is_director) fromDb.add('director');
  if (person.is_actor) fromDb.add('actor');

  const labels = ROLE_ORDER.filter((r) => fromDb.has(r)).map((r) => t(locale, ROLE_KEYS[r]));
  return labels.length > 0 ? labels.join(', ') : null;
}
