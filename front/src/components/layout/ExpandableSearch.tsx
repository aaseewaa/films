import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useTranslation } from '@/hooks/useTranslation';
import { cn } from '@/lib/utils';

interface ExpandableSearchProps {
  /** Родитель узнаёт, раскрыт ли поиск (сдвинуть навигацию) */
  onExpandedChange?: (expanded: boolean) => void;
  className?: string;
}

/** Соразмерно крупной навигации в Header (фильмы, Гении/вдохновители…) */
const ICON_BTN =
  'shrink-0 flex items-center justify-center bg-site-bg transition-colors hover:bg-site-hover w-[3.1rem] lg:w-[3.7rem] xl:w-[4.2rem]';
const ICON_SIZE = 'w-[1.75rem] h-[1.75rem] lg:w-[2.1rem] lg:h-[2.1rem] xl:w-[2.45rem] xl:h-[2.45rem]';

/**
 * Поиск: иконка соразмерна пунктам меню → по клику раскрывается крупная «капсула»,
 * остаётся открытой до клика вне или Escape.
 */
export function ExpandableSearch({ onExpandedChange, className }: ExpandableSearchProps) {
  const navigate = useNavigate();
  const tr = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const expanded = open;

  useEffect(() => {
    onExpandedChange?.(expanded);
  }, [expanded, onExpandedChange]);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  useEffect(() => {
    if (expanded) {
      const t = window.setTimeout(() => inputRef.current?.focus(), 80);
      return () => window.clearTimeout(t);
    }
  }, [expanded]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
      setOpen(false);
    }
  }

  return (
    <div
      ref={wrapRef}
      className={cn(
        'relative shrink-0 transition-transform duration-300 ease-out',
        expanded && 'scale-[1.04] lg:scale-[1.05]',
        className,
      )}
    >
      <form
        onSubmit={onSubmit}
        className={cn(
          'flex items-stretch rounded-full overflow-hidden',
          'bg-[#b5b5b5] transition-all duration-300 ease-out',
          expanded
            ? [
                'cursor-text',
                'h-[3.5rem] lg:h-[4.2rem] xl:h-[4.85rem]',
                'w-[min(100vw-2rem,300px)] sm:w-[360px] lg:w-[420px] xl:w-[480px]',
              ]
            : [
                'cursor-pointer',
                'h-[3.1rem] w-[3.1rem] lg:h-[3.7rem] lg:w-[3.7rem] xl:h-[4.2rem] xl:w-[4.2rem]',
              ],
        )}
        onClick={() => setOpen(true)}
      >
        <div className={cn(ICON_BTN, 'h-full')} aria-hidden>
          <Search strokeWidth={2.25} className={cn('text-ink-500', ICON_SIZE)} />
        </div>

        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder={tr('searchPlaceholder')}
          aria-label={tr('searchAria')}
          tabIndex={expanded ? 0 : -1}
          className={cn(
            'min-w-0 h-full bg-transparent text-ink-500 placeholder:text-ink-50/90',
            'font-semibold outline-none transition-opacity duration-200',
            'text-[1.15rem] lg:text-[1.4rem] xl:text-[1.65rem]',
            expanded ? 'flex-1 opacity-100 px-4 lg:px-5' : 'w-0 opacity-0 px-0 pointer-events-none',
          )}
        />
      </form>
    </div>
  );
}
