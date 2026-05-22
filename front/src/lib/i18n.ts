import type { SiteLocale } from '@/stores/locale';

export type UiKey =
  | 'navFilms'
  | 'navCollections'
  | 'navArticles'
  | 'navNews'
  | 'navGeniuses'
  | 'navInspirers'
  | 'searchPlaceholder'
  | 'searchAria'
  | 'searchTitle'
  | 'searchAll'
  | 'searchFilms'
  | 'searchPeople'
  | 'searchHybrid'
  | 'searchSemantic'
  | 'searchEmpty'
  | 'searchLoading'
  | 'searchError'
  | 'langSwitchToEn'
  | 'langSwitchToRu'
  | 'menuGraph'
  | 'menuAllFilms'
  | 'menuAllCollections'
  | 'menuJournal'
  | 'menuEditorial'
  | 'menuShowtimes'
  | 'menuAbout'
  | 'menuProfile'
  | 'menuFavorites'
  | 'menuRatings'
  | 'menuHistory'
  | 'menuLogout'
  | 'menuLogin'
  | 'menuRegister'
  | 'filmTabAbout'
  | 'filmTabCreators'
  | 'filmTabStills'
  | 'filmTabArticles'
  | 'filmTabSimilar'
  | 'filmTabAwards'
  | 'filmMore'
  | 'addToFavorites'
  | 'inFavorites'
  | 'favoriteError'
  | 'mediaFilm'
  | 'mediaSeries'
  | 'searchByTitle'
  | 'searchByMeaning'
  | 'searchHint'
  | 'searchFound'
  | 'searchTryOther';

const UI: Record<SiteLocale, Record<UiKey, string>> = {
  ru: {
    navFilms: 'фильмы',
    navCollections: 'коллекции',
    navArticles: 'статьи',
    navNews: 'новинки',
    navGeniuses: 'Гении',
    navInspirers: 'вдохновители',
    searchPlaceholder: 'Поиск...',
    searchAria: 'Поиск фильмов и режиссёров',
    searchTitle: 'Поиск',
    searchAll: 'Все',
    searchFilms: 'Фильмы',
    searchPeople: 'Люди',
    searchHybrid: 'Гибрид',
    searchSemantic: 'Смысл',
    searchEmpty: 'Ничего не найдено',
    searchLoading: 'Ищем…',
    searchError: 'Не удалось выполнить поиск',
    langSwitchToEn: 'Переключить на английский',
    langSwitchToRu: 'Переключить на русский',
    menuGraph: 'Открыть граф',
    menuAllFilms: 'Все фильмы',
    menuAllCollections: 'Все коллекции',
    menuJournal: 'Журнал',
    menuEditorial: 'Редакция',
    menuShowtimes: 'Афиша проката',
    menuAbout: 'О проекте',
    menuProfile: 'Профиль',
    menuFavorites: 'Избранное',
    menuRatings: 'Оценки',
    menuHistory: 'История',
    menuLogout: 'Выйти',
    menuLogin: 'Войти',
    menuRegister: 'Регистрация',
    filmTabAbout: 'О фильме',
    filmTabCreators: 'Создатели и актёры',
    filmTabStills: 'Кадры',
    filmTabArticles: 'Статьи',
    filmTabSimilar: 'Похожие фильмы',
    filmTabAwards: 'Награды',
    filmMore: 'Ещё',
    addToFavorites: 'Добавить в избранное',
    inFavorites: 'В избранном',
    favoriteError: 'Не удалось обновить избранное',
    mediaFilm: 'фильм',
    mediaSeries: 'сериал',
    searchByTitle: 'По названию',
    searchByMeaning: 'По смыслу',
    searchHint:
      'Введите запрос. Режим «По смыслу» ищет по описаниям через эмбеддинги, «По названию» — по тексту и опечаткам.',
    searchFound: 'Найдено',
    searchTryOther: 'Попробуйте другой запрос',
  },
  en: {
    navFilms: 'films',
    navCollections: 'collections',
    navArticles: 'articles',
    navNews: 'new releases',
    navGeniuses: 'Masters',
    navInspirers: 'of cinema',
    searchPlaceholder: 'Search...',
    searchAria: 'Search films and people',
    searchTitle: 'Search',
    searchAll: 'All',
    searchFilms: 'Films',
    searchPeople: 'People',
    searchHybrid: 'Hybrid',
    searchSemantic: 'Semantic',
    searchEmpty: 'No results found',
    searchLoading: 'Searching…',
    searchError: 'Search failed',
    langSwitchToEn: 'Switch to English',
    langSwitchToRu: 'Switch to Russian',
    menuGraph: 'Open graph',
    menuAllFilms: 'All films',
    menuAllCollections: 'All collections',
    menuJournal: 'Journal',
    menuEditorial: 'Editorial',
    menuShowtimes: 'Now playing',
    menuAbout: 'About',
    menuProfile: 'Profile',
    menuFavorites: 'Favorites',
    menuRatings: 'Ratings',
    menuHistory: 'History',
    menuLogout: 'Log out',
    menuLogin: 'Log in',
    menuRegister: 'Sign up',
    filmTabAbout: 'About',
    filmTabCreators: 'Cast & crew',
    filmTabStills: 'Stills',
    filmTabArticles: 'Articles',
    filmTabSimilar: 'Similar films',
    filmTabAwards: 'Awards',
    filmMore: 'More',
    addToFavorites: 'Add to favorites',
    inFavorites: 'In favorites',
    favoriteError: 'Could not update favorites',
    mediaFilm: 'film',
    mediaSeries: 'series',
    searchByTitle: 'By title',
    searchByMeaning: 'By meaning',
    searchHint:
      'Enter a query. “By meaning” searches descriptions via embeddings; “By title” matches text and typos.',
    searchFound: 'Found',
    searchTryOther: 'Try a different query',
  },
};

export function t(locale: SiteLocale, key: UiKey): string {
  return UI[locale][key];
}
