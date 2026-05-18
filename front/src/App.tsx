import { Routes, Route } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { HomePage } from '@/pages/HomePage';
import { FilmsPage } from '@/pages/FilmsPage';
import { FilmPage } from '@/pages/FilmPage';
import { ArticlesPage } from '@/pages/ArticlesPage';
import { ArticlePage } from '@/pages/ArticlePage';
import { CollectionsPage } from '@/pages/CollectionsPage';
import { CollectionPage } from '@/pages/CollectionPage';
import {
  DirectorPage,
  SearchPage,
  NewsPage,
  LoginPage,
  RegisterPage,
  ProfilePage,
  FavoritesPage,
  RatingsPage,
  HistoryPage,
  NotFoundPage,
} from '@/pages/Placeholders';

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        <Routes>
          {/* Главная — граф */}
          <Route path="/" element={<HomePage />} />

          {/* Карточки */}
          <Route path="/director/:id" element={<DirectorPage />} />
          <Route path="/film/:id" element={<FilmPage />} />

          {/* Каталоги */}
          <Route path="/films" element={<FilmsPage />} />
          <Route path="/search" element={<SearchPage />} />

          {/* Коллекции */}
          <Route path="/collections" element={<CollectionsPage />} />
          <Route path="/collection/:id" element={<CollectionPage />} />

          {/* Журнал */}
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/article/:slug" element={<ArticlePage />} />

          {/* Новинки */}
          <Route path="/news" element={<NewsPage />} />

          {/* Авторизация */}
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register" element={<RegisterPage />} />

          {/* Личный кабинет */}
          <Route path="/me" element={<ProfilePage />} />
          <Route path="/me/favorites" element={<FavoritesPage />} />
          <Route path="/me/ratings" element={<RatingsPage />} />
          <Route path="/me/history" element={<HistoryPage />} />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
