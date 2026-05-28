# FilmCine — фронтенд

Клиентская часть [информационной системы о кино](../README.md): каталог, карточки сущностей, радиальный граф влияний, поиск, журнал, коллекции, новинки и личный кабинет.

**Стек:** Vite · React 18 · TypeScript · Tailwind CSS · React Router 6 · TanStack Query · Zustand · Axios

---

## Требования

- **Node.js 18+** и npm
- Запущенный [backend](../backend/README.md) на `http://localhost:8000` (для API и `/uploads`)

---

## Запуск

### 1. Зависимости

```bash
cd front
npm install
```

### 2. Backend (отдельный терминал)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 3. Dev-сервер

```bash
cd front
npm run dev
```

Откройте [http://localhost:5173](http://localhost:5173).

Vite проксирует `/api` и `/uploads` на backend (`vite.config.ts`). Без БД и данных граф на главной будет пустым — см. [backend/scripts/README.md](../backend/scripts/README.md).

### Сборка

```bash
npm run build    # tsc + vite build → dist/
npm run preview  # просмотр production-сборки
```

---

## Маршруты

| Путь | Компонент | Назначение |
|------|-----------|------------|
| `/` | `HomePage` | Радиальный граф влияний (центр + кольца) |
| `/films` | `FilmsPage` | Каталог фильмов |
| `/film/:id` | `FilmPage` | Карточка фильма |
| `/director/:id` | `PersonPage` | Карточка персоны, подграф влияний |
| `/search` | `SearchPage` | Поиск (в т.ч. семантический) |
| `/articles` | `ArticlesPage` | Журнал |
| `/article/:slug` | `ArticlePage` | Статья |
| `/collections` | `CollectionsPage` | Подборки |
| `/collection/:id` | `CollectionPage` | Карточка подборки |
| `/news` | `NewsPage` | Новинки / афиша |
| `/auth/login`, `/auth/register` | — | Вход и регистрация |
| `/me`, `/me/favorites`, `/me/ratings`, `/me/history` | — | Личный кабинет |
| `*` | `NotFoundPage` | 404 |

Маршруты объявлены в `src/App.tsx`.

---

## Структура `src/`

```
src/
├── api/                 # HTTP-клиент (axios), типы, вызовы по доменам
├── components/
│   ├── layout/          # Header, поиск, меню, локаль
│   ├── ui/              # Базовые UI-элементы
│   ├── film/            # Блоки карточки фильма
│   ├── films/           # Каталог
│   ├── person/          # Карточка персоны, граф на странице
│   ├── articles/        # Журнал
│   ├── collections/     # Подборки
│   ├── news/            # Новинки
│   ├── search/          # Результаты поиска
│   ├── profile/         # Личный кабинет
│   ├── auth/            # Формы входа
│   └── user/            # Избранное и др.
├── pages/               # Страницы маршрутов (+ pages/me/)
├── stores/              # Zustand: auth, locale
├── hooks/               # React-хуки
├── lib/                 # Утилиты, i18n, вёрстка графа, ссылки в статьях
└── styles/              # global.css, Tailwind
```

Импорты через алиас `@/` → `src/` (см. `vite.config.ts`, `tsconfig.json`).

### API-слой

- `api/client.ts` — axios, JWT из `stores/auth`, параметр `lang` на каждый запрос
- Модули по доменам: `catalog`, `entity`, `graph`, `search`, `articles`, `collections`, `news`, `auth`, `userData`, …
- Общие типы: `api/types.ts`

---

## Граф на главной

Главная страница **не использует force-layout**: детерминированный **радиальный SVG** (центральный режиссёр, кольца влияний, вложенные орбиты). Логика позиций и анимаций — `lib/homeGraphLayout.ts`, данные — `api/graph.ts` (`/api/graph/...`).

Аналогичный радиальный подграф на карточке персоны: `components/person/PersonInfluencesGraph.tsx`.

---

## Локализация

- Язык UI: `stores/locale.ts`, переключатель в шапке (`LanguageToggle`)
- Запросы к API: query-параметр `lang` (`ru` / `en`) через `lib/siteLang.ts`
- Строки интерфейса: `lib/i18n.ts`, хук `hooks/useTranslation.ts`

---

## Дизайн

Токены в `tailwind.config.ts` и `lib/sitePalette.ts`.

| Назначение | Класс / значение |
|------------|------------------|
| Фон сайта | `bg-site-bg` — Alice Blue `#E1EFF6` |
| Hover фона | `bg-site-hover` — `#97D2FB` |
| Основной текст | `text-ink-300` |
| Акцент ссылок | `text-wine-500` |
| Акцент UI (фильтры, лого) | `text-tiffany` — `#0ABAB5` |
| Фон графа | `bg-graph-bg` (тот же светлый тон) |

**Шрифты:** Pluffy Loon — логотип и крупные заголовки каталога; Playfair Display / Lora — serif-заголовки; Inter — основной текст. Файлы шрифтов: `public/fonts/` (см. [public/fonts/README.md](public/fonts/README.md)).

Плашки статей — палитра в `ARTICLE_PLATE_COLORS` (`sitePalette.ts`).

---

## Реализованный функционал

- [x] Роутинг, общий layout, адаптивная шапка с поиском и меню
- [x] Главная: радиальный граф влияний, навигация в карточку персоны
- [x] Каталог фильмов, фильтры, карточка фильма (описание, создатели, рейтинг, кадры, афиша)
- [x] Карточка персоны: биография, фильмография, граф влияний
- [x] Семантический и обычный поиск
- [x] Журнал статей, подборки, новинки
- [x] JWT-авторизация, профиль, избранное, оценки, история
- [x] Двуязычный интерфейс (ru / en)
- [x] Страница 404

---

## Связанная документация

| Документ | Содержание |
|----------|------------|
| [../README.md](../README.md) | Обзор проекта и быстрый старт |
| [../backend/README.md](../backend/README.md) | API, `.env`, тесты |
| [../docs/WEEKLY_REPORT.md](../docs/WEEKLY_REPORT.md) | Архитектура и журнал разработки |
