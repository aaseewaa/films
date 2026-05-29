import { Fragment, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { ArticleEntityRef } from '@/api/types';
import { splitArticleTextWithPersonLinks } from '@/lib/articleEntityLinks';

/** Простой рендер body из seed: абзацы, **жирный**, ссылки на режиссёров */
export function splitArticleParagraphs(body: string): string[] {
  return body
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
}

export interface ParagraphToNodesOptions {
  relatedEntities?: ArticleEntityRef[];
  articleSlug?: string;
}

export function paragraphToNodes(
  text: string,
  options?: ParagraphToNodesOptions,
): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i}>
          {plainTextToNodes(part.slice(2, -2), options)}
        </strong>
      );
    }
    return <Fragment key={i}>{plainTextToNodes(part, options)}</Fragment>;
  });
}

function plainTextToNodes(
  text: string,
  options?: ParagraphToNodesOptions,
): ReactNode[] {
  const entities = options?.relatedEntities;
  if (!entities?.length) {
    return text ? [text] : [];
  }

  const segments = splitArticleTextWithPersonLinks(
    text,
    entities,
    options?.articleSlug,
  );
  return segments.map((seg, i) =>
    seg.kind === 'text' ? (
      <Fragment key={i}>{seg.value}</Fragment>
    ) : (
      <Link
        key={i}
        to={`/director/${seg.personId}`}
        className="text-tiffany hover:underline underline-offset-2 transition-colors"
      >
        {seg.value}
      </Link>
    ),
  );
}
