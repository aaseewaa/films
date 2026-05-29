import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listNews, listUpcoming } from '@/api/news';
import { NewsCarousel } from '@/components/news/NewsCarousel';
import { NewsFilmCard } from '@/components/news/NewsFilmCard';
import { NewsPlaceholderCard } from '@/components/news/NewsPlaceholderCard';
import { useAuthStore } from '@/stores/auth';
import { PageContent } from '@/components/layout/PageContent';
import { hasAfishaPoster } from '@/lib/newsAfisha';
import { useSiteLang } from '@/lib/siteLang';

const NEWS_PLACEHOLDERS = [
  {
    title: 'Фестиваль авторского кино откроет сезон',
    summary:
      'Редакция готовит обзор программы — материал появится в журнале после публикации в базе.',
    date: '15.05.2026',
  },
  {
    title: 'Интервью с режиссёром года',
    summary: 'Разговор о влияниях, монтаже и том, как меняется прокат в России.',
    date: '12.05.2026',
  },
  {
    title: 'Подборка: что смотреть в мае',
    summary: 'Короткий гид по премьерам и редким показам в артхаусных залах.',
    date: '08.05.2026',
  },
  {
    title: 'Новый взгляд на классику Нолана',
    summary: 'Эссе о времени и архитектуре сюжета — скоро на сайте.',
    date: '01.05.2026',
  },
] as const;

export function NewsPage() {
  const lang = useSiteLang();
  const { user, isAuthenticated } = useAuthStore();

  const { data: upcoming, isLoading: upcomingLoading } = useQuery({
    queryKey: ['news', 'upcoming', lang],
    queryFn: () => listUpcoming(10),
  });

  const { data: playing, isLoading: playingLoading } = useQuery({
    queryKey: ['news', 'world', lang],
    queryFn: () => listNews({ scope: 'world', limit: 12 }),
  });

  const playingFilms = (playing?.items ?? []).filter(hasAfishaPoster);
  const upcomingFilms = (upcoming?.items ?? []).filter(hasAfishaPoster);
  const featured = playingFilms.slice(0, 3);
  const gridFilms = playingFilms.slice(3);

  return (
    <div className="bg-site-bg min-h-[calc(100vh-5.75rem)] sm:min-h-[calc(100vh-6rem)] lg:min-h-[calc(100vh-6.5rem)]">
      <PageContent className="pt-8 sm:pt-10 pb-6">
        <p className="text-xs uppercase tracking-[0.2em] text-ink-50 mb-1">
          Прокат
        </p>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-500 mb-2">
          Новинки
        </h1>
        <p className="text-sm sm:text-base text-ink-100 max-w-2xl">
          Актуальная афиша мирового проката — только фильмы с постером из проката.{' '}
          {isAuthenticated && user?.city ? (
            <>
              Для города{' '}
              <strong className="text-ink-400">{user.city}</strong> — в разделе «Сейчас в кино».
            </>
          ) : (
            <>
              <Link to="/auth/register" className="text-wine-500 hover:underline">
                Зарегистрируйтесь
              </Link>
              , чтобы подставлять город в афишу.
            </>
          )}
        </p>
      </PageContent>

      <div className="space-y-12 sm:space-y-16 pb-12">
        {upcomingLoading ? (
          <p className="text-center text-ink-50 py-12">Загружаем премьеры…</p>
        ) : (
          <NewsCarousel
            title="Предстоящая афиша"
            films={upcomingFilms}
            metaLabel="СКОРО"
          />
        )}

        <PageContent as="section">
          <div className="mb-4 sm:mb-6">
            <p className="text-xs uppercase tracking-[0.2em] text-ink-50 mb-1">
              Сейчас в кино
            </p>
            <h2 className="font-serif text-2xl sm:text-3xl font-bold text-ink-500">
              Актуальная афиша
            </h2>
            {playing?.city && (
              <p className="text-sm text-ink-50 mt-1">{playing.city}</p>
            )}
          </div>

          {playingLoading && (
            <p className="text-center text-ink-50 py-16">Загружаем фильмы…</p>
          )}

          {!playingLoading && playingFilms.length === 0 && (
            <p className="text-center text-ink-50 py-16">
              Список проката временно недоступен.
            </p>
          )}

          {!playingLoading && featured.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[3px] mb-[3px]">
              {featured.map((film, i) => (
                <NewsFilmCard
                  key={`feat-${film.tmdb_id ?? film.title}`}
                  film={film}
                  index={i}
                  metaLabel="В ПРОКАТЕ"
                />
              ))}
            </div>
          )}

          {!playingLoading && gridFilms.length > 0 && (
            <div className="hidden lg:grid grid-cols-4 gap-[3px]">
              {gridFilms.map((film, i) => (
                <NewsFilmCard
                  key={`grid-${film.tmdb_id ?? film.title}`}
                  film={film}
                  index={i + 3}
                />
              ))}
            </div>
          )}

          {!playingLoading && gridFilms.length > 0 && (
            <div className="flex flex-col gap-[3px] lg:hidden">
              {gridFilms.map((film, i) => (
                <NewsFilmCard
                  key={`mob-${film.tmdb_id ?? film.title}`}
                  film={film}
                  index={i + 3}
                />
              ))}
            </div>
          )}
        </PageContent>

        <PageContent as="section" className="pt-4">
          <div className="mb-6 sm:mb-8">
            <h2 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-ink-500 tracking-tight">
              Новости
            </h2>
            <p className="text-sm text-ink-50 mt-2">
              Заглушки — позже подключим материалы из базы.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[3px]">
            {NEWS_PLACEHOLDERS.map((item, i) => (
              <NewsPlaceholderCard
                key={item.title}
                index={i}
                title={item.title}
                summary={item.summary}
                date={item.date}
              />
            ))}
          </div>
        </PageContent>
      </div>
    </div>
  );
}
