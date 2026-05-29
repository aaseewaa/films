import React from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
}

export function Button({
  className,
  variant = 'primary',
  size = 'md',
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-wine-500',
        'disabled:opacity-50 disabled:pointer-events-none',
        // variants
        variant === 'primary' &&
          'bg-wine-500 text-cream-50 hover:bg-wine-600',
        variant === 'ghost' &&
          'text-ink-300 hover:bg-site-hover',
        variant === 'outline' &&
          'border border-ink-50/30 text-ink-300 bg-site-bg hover:bg-site-hover',
        // sizes
        size === 'sm' && 'h-9 px-3 text-sm rounded-sm',
        size === 'md' && 'h-10 px-4 text-sm rounded-sm',
        size === 'lg' && 'h-12 px-6 text-base rounded-sm',
        className
      )}
      {...props}
    />
  );
}
