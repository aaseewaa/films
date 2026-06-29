import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useTranslation } from '@/hooks/useTranslation';
import { cn } from '@/lib/utils';
import { HEADER_CONTROL_HIT_CLASS, HEADER_CONTROL_ICON_CLASS } from '@/lib/headerNavTheme';

interface ExpandableSearchProps {
  /** Родитель сдвигает навигацию, когда поиск раскрыт */
  onExpandedChange?: (expanded: boolean) => void;
  className?: string;
}

const OPEN_OVAL_CLASS = cn(
  'flex items-stretch rounded-full overflow-hidden cursor-text',
  'bg-site-bg',
  'border border-tiffany/30',
  'shadow-[0_2px_14px_rgba(10,186,181,0.22),0_4px_24px_rgba(10,186,181,0.1)]',
  'h-[3.4rem] lg:h-[3.9rem] xl:h-[4.4rem]',
  'w-[min(88vw,280px)] sm:w-[320px] lg:w-[380px] xl:w-[440px]',
  'transition-all duration-300 ease-out',
);

/**
 * Поиск в шапке: до клика — только лупа; после — овал #E1EFF6 с тенью, лупа и | в tiffany.
 */
export function ExpandableSearch({ onExpandedChange, className }: ExpandableSearchProps) {
  const navigate = useNavigate();
  const tr = useTranslation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    onExpandedChange?.(open);
  }, [open, onExpandedChange]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false);
        setQuery('');
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  useEffect(() => {
    if (open) {
      const t = window.setTimeout(() => inputRef.current?.focus(), 60);
      return () => window.clearTimeout(t);
    }
  }, [open]);

  function collapseIfEmpty() {
    if (!query.trim()) {
      setOpen(false);
    }
  }

  function openSearch() {
    setOpen(true);
    inputRef.current?.focus();
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
      setOpen(false);
      setQuery('');
    }
  }

  return (
    <div
      ref={wrapRef}
      className={cn('relative shrink-0', className)}
      onMouseLeave={collapseIfEmpty}
    >
      <form onSubmit={onSubmit}>
        {!open ? (
          <button
            type="button"
            onClick={openSearch}
            className={cn(
              'shrink-0 rounded-sm text-tiffany hover:opacity-85 transition-opacity',
              HEADER_CONTROL_HIT_CLASS,
            )}
            aria-label={tr('searchAria')}
            aria-expanded={false}
          >
            <Search strokeWidth={2} className={HEADER_CONTROL_ICON_CLASS} aria-hidden />
          </button>
        ) : (
          <div className={OPEN_OVAL_CLASS} onClick={() => inputRef.current?.focus()}>
            <div
              className={cn(
                'shrink-0 flex items-center justify-center h-full text-tiffany',
                'w-[3.4rem] lg:w-[3.9rem] xl:w-[4.4rem]',
              )}
              aria-hidden
            >
              <Search strokeWidth={2.25} className={HEADER_CONTROL_ICON_CLASS} />
            </div>

            <div className="flex items-center flex-1 min-w-0 pr-4 lg:pr-5">
              {!query && (
                <span
                  className="text-tiffany font-semibold leading-none animate-pulse select-none mr-0.5"
                  aria-hidden
                >
                  |
                </span>
              )}
              <input
                ref={inputRef}
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setOpen(true)}
                placeholder=""
                aria-label={tr('searchAria')}
                className={cn(
                  'min-w-0 w-full h-full bg-transparent text-ink-500',
                  'font-semibold outline-none caret-tiffany',
                  'text-[1.05rem] lg:text-[1.2rem] xl:text-[1.45rem] 2xl:text-[1.75rem]',
                )}
              />
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
