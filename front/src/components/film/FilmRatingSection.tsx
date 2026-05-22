import { FilmRatingBlock } from '@/components/film/FilmRatingBlock';

interface FilmRatingSectionProps {
  entityId: number;
  voteAvg: string | null;
}

export function FilmRatingSection({ entityId, voteAvg }: FilmRatingSectionProps) {
  return (
    <div className="film-about-rating pt-8 sm:pt-10 lg:pt-12 max-w-3xl">
      <h3 className="text-xl sm:text-2xl uppercase tracking-wider text-ink-50 mb-4">
        Оценить фильм
      </h3>
      <FilmRatingBlock entityId={entityId} large />
      {voteAvg && (
        <p className="text-4xl font-bold text-ink-500 mt-6">TMDB: {voteAvg}</p>
      )}
    </div>
  );
}
