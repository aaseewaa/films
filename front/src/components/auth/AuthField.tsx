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
    <div className={cn('space-y-2', className)}>
      <label htmlFor={id} className="block text-2xl sm:text-3xl font-medium text-ink-400">
        {label}
      </label>
      {children}
      {error && <p className="text-2xl text-tiffany">{error}</p>}
    </div>
  );
}

export const authInputClass =
  'w-full h-28 px-8 text-2xl sm:text-3xl rounded-sm border-2 border-ink-50/20 bg-site-bg text-ink-400 placeholder:text-ink-50 hover:bg-site-hover focus:outline-none focus:ring-2 focus:ring-tiffany/30 focus:border-tiffany/40 focus:bg-site-hover transition-colors';

export const authSubmitButtonClass =
  'w-full h-28 text-2xl sm:text-3xl bg-tiffany text-white hover:bg-tiffany-dark focus-visible:ring-tiffany';

export const authFormClass = 'space-y-5';

export const authErrorClass =
  'text-2xl text-tiffany bg-tiffany/5 border-2 border-tiffany/20 rounded-sm px-8 py-4';
