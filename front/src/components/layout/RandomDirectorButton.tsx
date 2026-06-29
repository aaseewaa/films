import { cn } from '@/lib/utils';
import { HEADER_NAV_LINK_CLASS } from '@/lib/headerNavTheme';

interface RandomDirectorButtonProps {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}

export function RandomDirectorButton({
  onClick,
  disabled,
  className,
}: RandomDirectorButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'shrink-0 font-medium leading-tight whitespace-nowrap',
        'text-[#0ABAB5] px-3 lg:px-4 py-1.5 rounded border border-[#0ABAB5]/40',
        'hover:border-[#0ABAB5] transition-colors',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        HEADER_NAV_LINK_CLASS,
        className,
      )}
    >
      ↻ Случайный режиссёр
    </button>
  );
}
