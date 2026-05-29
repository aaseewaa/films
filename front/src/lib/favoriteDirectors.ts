/**
 * Пул центров графа на главной.
 *
 * Основной источник — GET /api/graph/centers (режиссёры с ≥2 входящими связями в БД).
 * FAVORITE_DIRECTORS — запасной список, если API недоступен.
 */

export interface FavoriteDirector {
  id: number;
  name: string;
}

/** Запасной список (10 классиков), если /api/graph/centers не ответил. */
export const FAVORITE_DIRECTORS: FavoriteDirector[] = [
  { id: 3217, name: 'Альфонсо Куарон' },
  { id: 3234, name: 'Сэм Мендес' },
  { id: 2172, name: 'Пол Томас Андерсон' },
  { id: 3219, name: 'Жак Риветт' },
  { id: 3243, name: 'Альфред Хичкок' },
  { id: 3281, name: 'Стэнли Кубрик' },
  { id: 2160, name: 'Мартин Скорсезе' },
  { id: 2216, name: 'Стивен Спилберг' },
  { id: 1520, name: 'Фрэнсис Форд Коппола' },
  { id: 1728, name: 'Квентин Тарантино' },
];

const SEEN_KEY = 'filmcine:graph:seenCenters';

/**
 * Случайный id из пула без повторов в рамках сессии.
 */
export function pickRandomCenterId(pool: { id: number }[]): number {
  if (pool.length === 0) {
    return FAVORITE_DIRECTORS[0].id;
  }

  const seen = JSON.parse(sessionStorage.getItem(SEEN_KEY) || '[]') as number[];
  let available = pool.filter((d) => !seen.includes(d.id));
  if (available.length === 0) {
    sessionStorage.removeItem(SEEN_KEY);
    available = pool;
  }

  const chosen = available[Math.floor(Math.random() * available.length)];
  sessionStorage.setItem(SEEN_KEY, JSON.stringify([...seen, chosen.id]));
  return chosen.id;
}

/** @deprecated Используй pickRandomCenterId(centers) после загрузки /api/graph/centers */
export function pickRandomFavorite(): FavoriteDirector {
  const id = pickRandomCenterId(FAVORITE_DIRECTORS);
  return FAVORITE_DIRECTORS.find((d) => d.id === id) ?? FAVORITE_DIRECTORS[0];
}
