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
  | 'searchTryOther'
  | 'mediaFilms'
  | 'pluralFilmFew'
  | 'pluralFilmMany'
  | 'pluralSeriesFew'
  | 'pluralSeriesMany'
  | 'pluralYearOne'
  | 'pluralYearFew'
  | 'pluralYearMany'
  | 'pluralWinOne'
  | 'pluralWinFew'
  | 'pluralWinMany'
  | 'pluralNominationOne'
  | 'pluralNominationFew'
  | 'pluralNominationMany'
  | 'personTabAbout'
  | 'personTabFilmography'
  | 'personTabInfluences'
  | 'personTabAwards'
  | 'personTabArticles'
  | 'personTabCollections'
  | 'personLoading'
  | 'personNotFound'
  | 'personBackToSearch'
  | 'personBreadcrumbHome'
  | 'personBreadcrumbPeople'
  | 'personFactsHeading'
  | 'personFilmographyEmpty'
  | 'personShowMore'
  | 'personCollapse'
  | 'personAwardWon'
  | 'personAwardNominated'
  | 'personInfluencesTitle'
  | 'personInfluencesCenter'
  | 'personInfluencesInMap'
  | 'personInfluencesHint'
  | 'personGraphLoading'
  | 'personGraphError'
  | 'authorLabel'
  | 'authorEditorial'
  | 'factBirthDate'
  | 'factDeathDate'
  | 'factBirthPlace'
  | 'factAwards'
  | 'roleDirector'
  | 'roleWriter'
  | 'roleActor'
  | 'roleProducer'
  | 'roleCinematographer'
  | 'roleComposer'
  | 'roleEditor'
  | 'roleProductionDesigner'
  | 'roleCostumeDesigner'
  | 'roleVoiceActor'
  | 'articleTypeEssay'
  | 'articleTypeReview'
  | 'articleTypeAnalysis'
  | 'articleTypeInterview'
  | 'articleTypeEditorial'
  | 'articleTypeRoundtable';

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
    mediaFilms: 'фильмов',
    pluralFilmFew: 'фильма',
    pluralFilmMany: 'фильмов',
    pluralSeriesFew: 'сериала',
    pluralSeriesMany: 'сериалов',
    pluralYearOne: 'год',
    pluralYearFew: 'года',
    pluralYearMany: 'лет',
    pluralWinOne: 'победа',
    pluralWinFew: 'победы',
    pluralWinMany: 'побед',
    pluralNominationOne: 'номинация',
    pluralNominationFew: 'номинации',
    pluralNominationMany: 'номинаций',
    personTabAbout: 'О персоне',
    personTabFilmography: 'Фильмография',
    personTabInfluences: 'Учителя / вдохновители',
    personTabAwards: 'Награды',
    personTabArticles: 'Публикации',
    personTabCollections: 'Подборки',
    personLoading: 'Загружаем…',
    personNotFound: 'Персона не найдена',
    personBackToSearch: '← К поиску',
    personBreadcrumbHome: 'Главная',
    personBreadcrumbPeople: 'Персоны',
    personFactsHeading: 'Сведения',
    personFilmographyEmpty: 'Фильмография пока не загружена.',
    personShowMore: 'Показать ещё',
    personCollapse: 'Свернуть',
    personAwardWon: 'Победа',
    personAwardNominated: 'Номинация',
    personInfluencesTitle: 'Учителя и вдохновители',
    personInfluencesCenter: 'Центр',
    personInfluencesInMap: 'в карте',
    personInfluencesHint:
      'Наведи на режиссёра — раскроется его круг · двойной клик — карточка',
    personGraphLoading: 'Строим граф…',
    personGraphError: 'Не удалось загрузить граф влияний',
    authorLabel: 'Автор',
    authorEditorial: 'Редакция FilmCine',
    factBirthDate: 'Дата рождения',
    factDeathDate: 'Дата смерти',
    factBirthPlace: 'Место рождения',
    factAwards: 'Награды',
    roleDirector: 'Режиссёр',
    roleWriter: 'Сценарист',
    roleActor: 'Актёр',
    roleProducer: 'Продюсер',
    roleCinematographer: 'Оператор',
    roleComposer: 'Композитор',
    roleEditor: 'Монтажёр',
    roleProductionDesigner: 'Художник-постановщик',
    roleCostumeDesigner: 'Художник по костюмам',
    roleVoiceActor: 'Озвучка',
    articleTypeEssay: 'Эссе',
    articleTypeReview: 'Рецензия',
    articleTypeAnalysis: 'Анализ',
    articleTypeInterview: 'Интервью',
    articleTypeEditorial: 'Редакция',
    articleTypeRoundtable: 'Круглый стол',
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
    mediaFilms: 'films',
    pluralFilmFew: 'films',
    pluralFilmMany: 'films',
    pluralSeriesFew: 'series',
    pluralSeriesMany: 'series',
    pluralYearOne: 'year',
    pluralYearFew: 'years',
    pluralYearMany: 'years',
    pluralWinOne: 'win',
    pluralWinFew: 'wins',
    pluralWinMany: 'wins',
    pluralNominationOne: 'nomination',
    pluralNominationFew: 'nominations',
    pluralNominationMany: 'nominations',
    personTabAbout: 'About',
    personTabFilmography: 'Filmography',
    personTabInfluences: 'Teachers & inspirations',
    personTabAwards: 'Awards',
    personTabArticles: 'Publications',
    personTabCollections: 'Collections',
    personLoading: 'Loading…',
    personNotFound: 'Person not found',
    personBackToSearch: '← Back to search',
    personBreadcrumbHome: 'Home',
    personBreadcrumbPeople: 'People',
    personFactsHeading: 'Details',
    personFilmographyEmpty: 'Filmography not loaded yet.',
    personShowMore: 'Show more',
    personCollapse: 'Collapse',
    personAwardWon: 'Won',
    personAwardNominated: 'Nomination',
    personInfluencesTitle: 'Teachers & inspirations',
    personInfluencesCenter: 'Center',
    personInfluencesInMap: 'in map',
    personInfluencesHint:
      'Hover a director to expand their circle · double-click for profile',
    personGraphLoading: 'Building graph…',
    personGraphError: 'Could not load influence graph',
    authorLabel: 'Author',
    authorEditorial: 'FilmCine Editorial',
    factBirthDate: 'Date of birth',
    factDeathDate: 'Date of death',
    factBirthPlace: 'Place of birth',
    factAwards: 'Awards',
    roleDirector: 'Director',
    roleWriter: 'Writer',
    roleActor: 'Actor',
    roleProducer: 'Producer',
    roleCinematographer: 'Cinematographer',
    roleComposer: 'Composer',
    roleEditor: 'Editor',
    roleProductionDesigner: 'Production designer',
    roleCostumeDesigner: 'Costume designer',
    roleVoiceActor: 'Voice actor',
    articleTypeEssay: 'Essay',
    articleTypeReview: 'Review',
    articleTypeAnalysis: 'Analysis',
    articleTypeInterview: 'Interview',
    articleTypeEditorial: 'Editorial',
    articleTypeRoundtable: 'Roundtable',
  },
};

export function t(locale: SiteLocale, key: UiKey): string {
  return UI[locale][key];
}
