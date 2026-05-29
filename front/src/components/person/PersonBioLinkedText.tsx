import { Link } from 'react-router-dom';
import type { PersonFilmographyItem } from '@/api/types';
import { splitBioTextWithFilmLinks } from '@/lib/personBioFilmLinks';

interface PersonBioLinkedTextProps {
  text: string;
  filmography: PersonFilmographyItem[];
  className?: string;
}

export function PersonBioLinkedText({
  text,
  filmography,
  className,
}: PersonBioLinkedTextProps) {
  return (
    <span className={className}>
      <LineWithFilmLinks line={text} filmography={filmography} />
    </span>
  );
}

function LineWithFilmLinks({
  line,
  filmography,
}: {
  line: string;
  filmography: PersonFilmographyItem[];
}) {
  const segments = splitBioTextWithFilmLinks(line, filmography);

  return (
    <>
      {segments.map((seg, i) =>
        seg.kind === 'text' ? (
          <span key={i}>{seg.value}</span>
        ) : (
          <Link
            key={i}
            to={`/film/${seg.filmId}`}
            className="text-[#97D2FB] hover:underline underline-offset-2 transition-colors"
          >
            {seg.value}
          </Link>
        ),
      )}
    </>
  );
}
