import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Утилита для объединения классов tailwind с правильной приоритизацией.
 * cn('px-2 py-1', 'px-4') => 'py-1 px-4'  (px-4 побеждает)
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
