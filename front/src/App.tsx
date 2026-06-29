import { Routes, Route } from 'react-router-dom';
import { Header } from '@/components/layout/Header';
import { LocaleSync } from '@/components/layout/LocaleSync';
import { GraphHeaderProvider } from '@/contexts/GraphHeaderContext';
import { HomePage } from '@/pages/HomePage';
import { FilmsPage } from '@/pages/FilmsPage';
import { FilmPage } from '@/pages/FilmPage';
import { ArticlesPage } from '@/pages/ArticlesPage';
import { ArticlePage } from '@/pages/ArticlePage';
import { CollectionsPage } from '@/pages/CollectionsPage';
import { CollectionPage } from '@/pages/CollectionPage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { NewsPage } from '@/pages/NewsPage';
import { SearchPage } from '@/pages/SearchPage';
import { PersonPage as DirectorPage } from '@/pages/PersonPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { FavoritesPage } from '@/pages/me/FavoritesPage';
import { RatingsPage } from '@/pages/me/RatingsPage';
import { HistoryPage } from '@/pages/me/HistoryPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

function App() {
  return (
    <div className="min-h-screen flex flex-col bg-site-bg">
      <LocaleSync />
      <GraphHeaderProvider>
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
      </GraphHeaderProvider>
    </div>
  );
}

export default App;
