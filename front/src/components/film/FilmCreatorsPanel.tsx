import { Link } from 'react-router-dom';
import type { FilmDetail, PersonRef } from '@/api/types';
import { formatPersonWorkLine } from '@/lib/personFilmographyLine';
import { cn } from '@/lib/utils';

const SIDEBAR_ITEMS = [
  { id: 'creators-directors', label: 'Режиссёры', has: (f: FilmDetail) => (f.directors?.length ?? 0) > 0 },
  { id: 'creators-cast', label: 'Актёры', has: (f: FilmDetail) => (f.cast?.length ?? 0) > 0 },
] as const;

const PHOTO_CLASS =
  'shrink-0 object-cover object-top bg-cream-200 group-hover:opacity-90 w-44 h-44 sm:w-52 sm:h-52 lg:w-60 lg:h-60 xl:w-64 xl:h-64';

function PersonRow({
  person,
  showCharacter,
}: {
  person: PersonRef;
  showCharacter?: boolean;
}) {
  const workLine = formatPersonWorkLine(person, showCharacter ? 'actor' : 'director');

  return (
    <Link
      to={`/director/${person.id}`}
      className="flex flex-row items-start gap-6 sm:gap-10 py-6 sm:py-8 border-b border-ink-50/12 last:border-0 hover:bg-site-hover transition-colors group text-left w-full"
    >
      {person.images.primary ? (
        <img src={person.images.primary} alt="" className={PHOTO_CLASS} />
      ) : (
        <div className={cn(PHOTO_CLASS, 'bg-cream-300')} />
      )}
      <div className="min-w-0 pt-0 sm:pt-1 flex-1">
        <p className="text-2xl sm:text-3xl lg:text-4xl font-bold text-ink-500 group-hover:text-ink-400 leading-snug">
          {person.title}
        </p>
        {person.title_en && person.title_en !== person.title && (
          <p className="text-lg sm:text-xl lg:text-2xl text-ink-50 mt-1 sm:mt-2 leading-snug">
            {person.title_en}
          </p>
        )}
        {showCharacter && person.character_name && (
          <p className="text-xl sm:text-2xl text-ink-300 mt-2 sm:mt-3 leading-snug">
            {person.character_name}
          </p>
        )}
        {workLine && (
          <p className="text-lg sm:text-xl text-ink-300 mt-2 sm:mt-3 leading-snug">{workLine}</p>
        )}
      </div>
    </Link>
  );
}

interface FilmCreatorsPanelProps {
  film: FilmDetail;
  metaLine: string;
}

export function FilmCreatorsPanel({ film, metaLine }: FilmCreatorsPanelProps) {
  const directors = film.directors ?? [];
  const cast = film.cast ?? [];
  const navItems = SIDEBAR_ITEMS.filter((item) => item.has(film));

  return (
    <div>
      <header className="text-center max-w-4xl mx-auto mb-10 sm:mb-14">
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-ink-500 leading-tight">
          <span className="block">Создатели фильма {film.title}</span>
          <span className="block mt-2 sm:mt-3 text-2xl sm:text-3xl lg:text-4xl font-semibold text-ink-400">
            режиссёры, актёры, съёмочная группа
          </span>
        </h1>
        {metaLine && (
          <p className="mt-5 sm:mt-6 text-base sm:text-lg lg:text-xl text-ink-50 leading-relaxed uppercase tracking-[0.12em] sm:tracking-[0.14em]">
            {metaLine}
          </p>
        )}
      </header>

      <div className="flex flex-col lg:flex-row gap-8 lg:gap-12 w-full items-start">
        {navItems.length > 0 && (
          <nav className="lg:w-44 xl:w-48 shrink-0">
            <ul className="flex flex-wrap lg:flex-col gap-4 lg:gap-4 text-sm sm:text-base uppercase tracking-[0.14em] font-bold text-ink-50">
              {navItems.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    className="hover:text-ink-500 transition-colors"
                    onClick={(e) => {
                      e.preventDefault();
                      document.getElementById(item.id)?.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start',
                      });
                    }}
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}

        <div className="flex-1 min-w-0 w-full">
          {directors.length > 0 && (
            <section
              id="creators-directors"
              className="scroll-mt-28 mb-12 sm:mb-16 text-left"
            >
              <h2 className="text-2xl sm:text-3xl font-bold text-ink-500 mb-4 sm:mb-6">Режиссёр</h2>
              {directors.map((d) => (
                <PersonRow key={d.id} person={d} />
              ))}
            </section>
          )}

          {cast.length > 0 && (
            <section id="creators-cast" className="scroll-mt-28 text-left">
              <h2 className="text-2xl sm:text-3xl font-bold text-ink-500 mb-4 sm:mb-6">Актёры</h2>
              {cast.map((p) => (
                <PersonRow key={p.id} person={p} showCharacter />
              ))}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
