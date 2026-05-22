export { PersonPage as DirectorPage } from '@/pages/PersonPage';

export { ProfilePage } from '@/pages/ProfilePage';
export { FavoritesPage } from '@/pages/me/FavoritesPage';
export { RatingsPage } from '@/pages/me/RatingsPage';
export { HistoryPage } from '@/pages/me/HistoryPage';

export function NotFoundPage() {
  return (
    <Placeholder>
      <span className="text-h1 font-serif block mb-4">404</span>
      Страницы не существует
      <br />
      <Link to="/" className="text-wine-500 hover:underline mt-4 inline-block">
        ← На главную
      </Link>
    </Placeholder>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <PageContent className="py-24">
      <div className="text-center text-ink-100">
        <div className="font-serif text-2xl">{children}</div>
      </div>
    </PageContent>
  );
}
