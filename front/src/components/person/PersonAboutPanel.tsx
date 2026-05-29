import type { PersonFilmographyItem } from '@/api/types';
import { PersonBioLinkedText } from '@/components/person/PersonBioLinkedText';
import type { PersonBioParts } from '@/lib/personBio';

interface PersonAboutPanelProps {
  bio: PersonBioParts;
  filmography: PersonFilmographyItem[];
}

/** Убирает «мягкие» переносы из вики, оставляет только абзацы. */
function bioParagraphs(body: string): string[] {
  const normalized = body
    .replace(/\r\n/g, '\n')
    .replace(/([^\n])\n([^\n])/g, '$1 $2')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  return normalized.split(/\n\n+/).filter((p) => p.trim());
}

export function PersonAboutPanel({ bio, filmography }: PersonAboutPanelProps) {
  const hasText = Boolean(bio.lead || bio.body);
  const textClass =
    'text-xl sm:text-2xl lg:text-3xl text-ink-300 leading-relaxed';

  if (!hasText) {
    return (
      <p className={`${textClass} text-ink-50`}>Биография пока не добавлена.</p>
    );
  }

  return (
    <div className="w-full max-w-none space-y-6 sm:space-y-8">
      {bio.lead && (
        <p className={`${textClass} text-left`}>
          <PersonBioLinkedText
            text={bioParagraphs(bio.lead).join(' ') || bio.lead}
            filmography={filmography}
          />
        </p>
      )}
      {bio.body && (
        <div className={`prose-essay-person w-full max-w-none space-y-6 sm:space-y-8 ${textClass}`}>
          {bioParagraphs(bio.body).map((para, i) => (
            <p key={i} className="text-left">
              <PersonBioLinkedText text={para} filmography={filmography} />
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
