import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExpandableSearchProps {
  /** Родитель узнаёт, раскрыт ли поиск (сдвинуть навигацию) */
  onExpandedChange?: (expanded: boolean) => void;
  className?: string;
}

/**
 * Поиск: иконка → при наведении/фокусе раскрывается «капсула» влево,
 * соседние пункты меню сдвигаются за счёт flex.
 */
export function ExpandableSearch({ onExpandedChange, className }: ExpandableSearchProps) {
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [query, setQuery] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const expanded = hovered || pinned;

  useEffect(() => {
    onExpandedChange?.(expanded);
  }, [expanded, onExpandedChange]);

  useEffect(() => {
    if (!pinned) return;
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setPinned(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setPinned(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [pinned]);

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
      setPinned(false);
      setHovered(false);
    }
  }

  return (
    <div
      ref={wrapRef}
      className={cn('relative shrink-0', className)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        if (!pinned && document.activeElement !== inputRef.current) {
          setHovered(false);
        }
      }}
    >
      <form
        onSubmit={onSubmit}
        className={cn(
          'flex items-stretch h-10 rounded-full overflow-hidden',
          'bg-[#b5b5b5] transition-[width] duration-300 ease-out',
          expanded ? 'w-[min(100vw-2rem,280px)] sm:w-[300px] lg:w-[340px]' : 'w-10 cursor-pointer',
        )}
        onClick={() => {
          if (!expanded) {
            setPinned(true);
            setHovered(true);
          }
        }}
      >
        <div
          className="w-10 h-10 shrink-0 bg-white flex items-center justify-center"
          aria-hidden
        >
          <Search size={20} strokeWidth={2} className="text-ink-500" />
        </div>

        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setPinned(true)}
          placeholder="Поиск..."
          aria-label="Поиск фильмов и режиссёров"
          tabIndex={expanded ? 0 : -1}
          className={cn(
            'h-10 min-w-0 bg-transparent text-ink-500 placeholder:text-ink-50/90',
            'text-sm outline-none transition-opacity duration-200',
            expanded ? 'flex-1 opacity-100 px-3' : 'w-0 opacity-0 px-0 pointer-events-none',
          )}
        />
      </form>
    </div>
  );
}
