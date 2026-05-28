import { Link } from 'react-router-dom';
import { PageContent } from '@/components/layout/PageContent';

export function NotFoundPage() {
  return (
    <PageContent className="py-24">
      <div className="text-center text-ink-100">
        <span className="text-h1 font-serif block mb-4">404</span>
        <div className="font-serif text-2xl">Страницы не существует</div>
        <Link to="/" className="text-wine-500 hover:underline mt-4 inline-block">
          ← На главную
        </Link>
      </div>
    </PageContent>
  );
}
