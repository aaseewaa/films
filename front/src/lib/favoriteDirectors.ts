/**
 * Топ-10 «любимых» режиссёров для рандомного центра графа на главной.
 * Каждый раз когда пользователь заходит на сайт — случайный центр.
 *
 * ID соответствуют записям в твоей БД (person.id с is_director=true).
 * Если ID не совпадает — поправь здесь.
 */
export interface FavoriteDirector {
  id: number;
  name: string;
  hint?: string; // для отладки
}

export const FAVORITE_DIRECTORS: FavoriteDirector[] = [
  { id: 3217, name: 'Альфонсо Куарон',   hint: '20 связей' },
  { id: 3234, name: 'Сэм Мендес',         hint: '10 связей' },
  { id: 2172, name: 'Пол Томас Андерсон', hint: '9 связей' },
  { id: 3219, name: 'Жак Риветт',         hint: '5 связей' },
  { id: 3243, name: 'Альфред Хичкок',     hint: 'Хичкок' },
  { id: 3281, name: 'Стэнли Кубрик',      hint: 'Kubrick' },
  { id: 2160, name: 'Мартин Скорсезе',    hint: 'Scorsese' },
  { id: 2216, name: 'Стивен Спилберг',    hint: 'Spielberg' },
  { id: 1520, name: 'Фрэнсис Форд Коппола', hint: 'Coppola' },
  { id: 1728, name: 'Квентин Тарантино',  hint: 'Tarantino' },
  // Из топ-15 БД (proven хабы):
  // Pryor(10), Аллен(6), Хоукс(5), Скорсезе(4), Спилберг(4), Disney(4), Ford(4)
  // Если знаешь их ID — добавь сюда вручную через SQL запрос:
  //   SELECT et.title, p.id FROM person p
  //   JOIN entity_translation et ON et.entity_id = p.id
  //     AND et.language_id = (SELECT id FROM language WHERE code='ru')
  //   WHERE p.is_director = true
  //     AND et.title IN ('Вуди Аллен','Мартин Скорсезе','Стивен Спилберг','Уолт Дисней');
];

/**
 * Возвращает случайного режиссёра из списка.
 * Использует sessionStorage чтобы избежать повторов в рамках одной сессии:
 * каждый раз новый, пока не пройдём весь список.
 */
export function pickRandomFavorite(): FavoriteDirector {
  const seenKey = 'filmcine:graph:seenCenters';
  const seen = JSON.parse(sessionStorage.getItem(seenKey) || '[]') as number[];

  let available = FAVORITE_DIRECTORS.filter((d) => !seen.includes(d.id));
  if (available.length === 0) {
    sessionStorage.removeItem(seenKey);
    available = FAVORITE_DIRECTORS;
  }

  const chosen = available[Math.floor(Math.random() * available.length)];
  sessionStorage.setItem(seenKey, JSON.stringify([...seen, chosen.id]));
  return chosen;
}
