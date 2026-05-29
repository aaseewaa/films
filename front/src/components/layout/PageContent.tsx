import type { ElementType, ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageContentProps {
  children: ReactNode;
  className?: string;
  as?: ElementType;
}

/** Центральная колонка сайта (~88% ширины, поля как kinomania). Не использовать на странице графа (/). */
export function PageContent({ children, className, as: Tag = 'div' }: PageContentProps) {
  return <Tag className={cn('page-content', className)}>{children}</Tag>;
}
