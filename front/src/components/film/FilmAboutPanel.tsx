import type { FilmDetail } from '@/api/types';
import { buildFilmFacts } from '@/lib/filmFacts';

interface FilmAboutPanelProps {
  film: FilmDetail;
  aboutText: { lead: string | null; body: string | null };
}

/** Описание + боковые «Сведения»; оценка вынесена отдельно (ближе к создателям). */
export function FilmAboutPanel({ film, aboutText }: FilmAboutPanelProps) {
  const facts = buildFilmFacts(film);
  const hasText = Boolean(aboutText.lead || aboutText.body);

  return (
    <div className="film-about-layout lg:grid lg:grid-cols-[minmax(0,56%)_minmax(260px,1fr)] lg:gap-x-8 xl:gap-x-12 items-start">
      <div className="min-w-0 film-about-text-col">
        {hasText && (
          <div className="space-y-6">
            {aboutText.lead && (
              <p className="text-2xl sm:text-4xl text-ink-300 leading-relaxed">{aboutText.lead}</p>
            )}
            {aboutText.body && (
              <div className="prose-essay-film text-ink-300 whitespace-pre-line">{aboutText.body}</div>
            )}
          </div>
        )}
      </div>

      {facts.length > 0 && (
        <aside className="mt-10 lg:mt-0 film-about-facts-col">
          <h3 className="text-lg sm:text-xl uppercase tracking-wider text-ink-50 mb-4 lg:mb-5">
            Сведения
          </h3>
          <dl className="space-y-4 text-lg sm:text-xl lg:text-2xl text-ink-300">
            {facts.map((row) => (
              <div key={row.label}>
                <dt className="text-ink-50 text-base sm:text-lg mb-0.5">{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </aside>
      )}
    </div>
  );
}
