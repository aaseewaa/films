import { cn } from '@/lib/utils';

interface AuthFieldProps {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}

export function AuthField({ id, label, error, children, className }: AuthFieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-ink-400">
        {label}
      </label>
      {children}
      {error && <p className="text-sm text-wine-500">{error}</p>}
    </div>
  );
}

export const authInputClass =
  'w-full h-11 px-3 rounded-sm border border-ink-50/20 bg-site-bg text-ink-400 placeholder:text-ink-50 hover:bg-site-hover focus:outline-none focus:ring-2 focus:ring-wine-500/30 focus:border-wine-500/40 focus:bg-site-hover transition-colors';
