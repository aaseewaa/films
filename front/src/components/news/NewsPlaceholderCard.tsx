import { themeForIndex } from '@/lib/newsCardTheme';
import { cn } from '@/lib/utils';

interface NewsPlaceholderCardProps {
  index: number;
  title: string;
  summary: string;
  date: string;
}

export function NewsPlaceholderCard({
  index,
  title,
  summary,
  date,
}: NewsPlaceholderCardProps) {
  const theme = themeForIndex(index + 3);
  const meta = `НОВОСТИ / ${date}`;

  return (
    <article className="flex flex-col min-h-0 opacity-90">
      <div className="relative w-full aspect-square overflow-hidden bg-[#d8d8d8] flex items-center justify-center">
        <span className="text-xs uppercase tracking-[0.2em] text-ink-50">Скоро</span>
      </div>
      <div
        className="flex flex-col p-4 sm:p-5 md:p-6 min-h-[160px] flex-1"
        style={{ backgroundColor: theme.bg }}
      >
        <p
          className={cn(
            'text-[0.625rem] sm:text-[0.6875rem] uppercase tracking-[0.18em] font-medium mb-2',
            theme.textLight ? 'text-white/85' : 'text-ink-500/75',
          )}
        >
          {meta}
        </p>
        <h3
          className={cn(
            'font-serif font-bold text-base sm:text-lg leading-snug mb-2',
            theme.textLight ? 'text-white' : 'text-ink-500',
          )}
        >
          {title}
        </h3>
        <p
          className={cn(
            'text-xs sm:text-sm leading-relaxed line-clamp-4',
            theme.textLight ? 'text-white/95' : 'text-ink-400',
          )}
        >
          {summary}
        </p>
      </div>
    </article>
  );
}
