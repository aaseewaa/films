import type { EntityDetail } from '@/api/types';

/** Режиссёрские или актёрские работы — как в шапке PersonHero. */
export function personWorkMode(person: EntityDetail): 'director' | 'actor' {
  return person.is_director ? 'director' : 'actor';
}
