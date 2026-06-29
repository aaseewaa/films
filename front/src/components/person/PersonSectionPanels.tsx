import { useState } from 'react';
import type {
  ArticleSummary,
  CollectionSummary,
  EntityDetail,
  PersonAwardItem,
  PersonFilmographyItem,
} from '@/api/types';
import { PersonInfluencesGraph } from '@/components/person/PersonInfluencesGraph';
import { useTranslation } from '@/hooks/useTranslation';
import { personHeroPlate } from '@/lib/personHeroTheme';
import { ArticleJournalGrid } from '@/components/articles/ArticleJournalGrid';
import { CollectionCatalogCard } from '@/components/collections/CollectionCatalogCard';
import { PersonFilmographyCard } from '@/components/person/PersonFilmographyCard';
import { formatAwardLine } from '@/lib/personFacts';

export function PersonInfluencesPanel({ person }: { person: EntityDetail }) {
  const plate = personHeroPlate(person);
  return (
    <PersonInfluencesGraph
      directorId={person.id}
      directorName={person.title}
      plate={plate}
    />
  );
}

const FILMOGRAPHY_PREVIEW = 3;

export function PersonFilmographyPanel({ items }: { items: PersonFilmographyItem[] }) {
  const tr = useTranslation();
  const [showAll, setShowAll] = useState(false);

  if (!items.length) {
    return (
      <p className="text-xl sm:text-2xl lg:text-3xl text-ink-50">
        {tr('personFilmographyEmpty')}
      </p>
    );
  }

  const hasMore = items.length > FILMOGRAPHY_PREVIEW;
  const visible = showAll ? items : items.slice(0, FILMOGRAPHY_PREVIEW);
  const hiddenCount = items.length - FILMOGRAPHY_PREVIEW;

  return (
    <div>
      {visible.map((film) => (
        <PersonFilmographyCard key={film.id} film={film} />
      ))}

      {hasMore && !showAll && (
        <div className="pt-6 sm:pt-8 border-t border-ink-50/15">
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="text-xl sm:text-2xl lg:text-3xl font-medium text-ink-300 hover:text-ink-500 transition-colors"
          >
            {tr('personShowMore')} ({hiddenCount})
          </button>
        </div>
      )}

      {hasMore && showAll && (
        <div className="pt-6 sm:pt-8">
          <button
            type="button"
            onClick={() => setShowAll(false)}
            className="text-lg sm:text-xl text-ink-50 hover:text-ink-300 transition-colors"
          >
            {tr('personCollapse')}
          </button>
        </div>
      )}
    </div>
  );
}

export function PersonAwardsPanel({ items }: { items: PersonAwardItem[] }) {
  const tr = useTranslation();

  return (
    <ul className="space-y-4 sm:space-y-5">
      {items.map((item, i) => (
        <li
          key={`${item.year}-${item.award_name}-${i}`}
          className="flex flex-wrap gap-x-4 gap-y-1 text-lg sm:text-xl lg:text-2xl text-ink-300"
        >
          <span
            className={
              item.status === 'won'
                ? 'shrink-0 text-xs sm:text-sm uppercase tracking-wide font-medium text-wine-500'
                : 'shrink-0 text-xs sm:text-sm uppercase tracking-wide font-medium text-ink-50'
            }
          >
            {item.status === 'won' ? tr('personAwardWon') : tr('personAwardNominated')}
          </span>
          <span>{formatAwardLine(item)}</span>
        </li>
      ))}
    </ul>
  );
}

export function PersonArticlesPanel({ articles }: { articles: ArticleSummary[] }) {
  return <ArticleJournalGrid articles={articles} />;
}

export function PersonCollectionsPanel({ collections }: { collections: CollectionSummary[] }) {
  return (
    <div>
      {collections.map((c) => (
        <CollectionCatalogCard key={c.id} collection={c} />
      ))}
    </div>
  );
}
