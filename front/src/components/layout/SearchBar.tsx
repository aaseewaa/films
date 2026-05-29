import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  className?: string;
  placeholder?: string;
  /** pill — белая капсула как на макете графа */
  variant?: 'default' | 'pill';
}

export function SearchBar({
  className,
  placeholder = 'Поиск фильмов и режиссёров...',
  variant = 'default',
}: SearchBarProps) {
  const [value, setValue] = useState('');
  const navigate = useNavigate();

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  }

  const isPill = variant === 'pill';

  return (
    <form
      onSubmit={onSubmit}
      className={cn('relative shrink-0', isPill ? 'w-[200px] sm:w-[240px]' : 'w-full', className)}
    >
      <Search
        className={cn(
          'absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none',
          isPill ? 'text-ink-400' : 'text-ink-50',
        )}
        size={isPill ? 16 : 18}
      />
      <input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={isPill ? '' : placeholder}
        aria-label={placeholder || 'Поиск'}
        className={cn(
          'w-full text-sm transition-colors focus:outline-none',
          isPill
            ? 'h-9 pl-9 pr-4 rounded-full bg-site-bg text-ink-300 placeholder:text-ink-50/80 hover:bg-site-hover focus:ring-2 focus:ring-site-hover/50 focus:bg-site-hover transition-colors'
            : cn(
                'h-10 pl-10 pr-4 rounded-sm',
                'bg-site-bg border border-ink-50/15',
                'text-ink-300 placeholder:text-ink-50 hover:bg-site-hover',
                'focus:border-wine-500 focus:bg-site-hover',
              ),
        )}
      />
    </form>
  );
}
