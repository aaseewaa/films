import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addFavorite,
  checkFavorite,
  removeFavorite,
} from '@/api/userData';
import { useTranslation } from '@/hooks/useTranslation';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

const HEART_SIZE = 28;

function heartClass(isFavorite: boolean) {
  return cn(
    'transition-colors',
    isFavorite
      ? 'text-tiffany fill-tiffany hover:text-tiffany-dark hover:fill-tiffany-dark'
      : 'text-black fill-none hover:text-ink-300',
  );
}

interface FavoriteButtonProps {
  entityId: number;
  className?: string;
}

export function FavoriteButton({ entityId, className }: FavoriteButtonProps) {
  const tr = useTranslation();
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const { data: check } = useQuery({
    queryKey: ['favorite', 'check', entityId],
    queryFn: () => checkFavorite(entityId),
    enabled: isAuthenticated && entityId > 0,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['favorite', 'check', entityId] });
    queryClient.invalidateQueries({ queryKey: ['favorites'] });
    queryClient.invalidateQueries({ queryKey: ['profile', 'favorites'] });
    queryClient.invalidateQueries({ queryKey: ['profile', 'stats'] });
  };

  const addMutation = useMutation({
    mutationFn: () => addFavorite(entityId),
    onSuccess: invalidate,
  });

  const removeMutation = useMutation({
    mutationFn: () => removeFavorite(entityId),
    onSuccess: invalidate,
  });

  const isFavorite = check?.is_favorite ?? false;
  const pending = addMutation.isPending || removeMutation.isPending;
  const hasError = addMutation.isError || removeMutation.isError;
  const ariaLabel = isFavorite ? tr('inFavorites') : tr('addToFavorites');

  if (!isAuthenticated) {
    return (
      <Link
        to="/auth/login"
        className={cn('inline-flex', className)}
        aria-label={tr('addToFavorites')}
      >
        <Heart size={HEART_SIZE} strokeWidth={1.75} className={heartClass(false)} />
      </Link>
    );
  }

  function handleToggle() {
    if (isFavorite) {
      removeMutation.mutate();
    } else {
      addMutation.mutate();
    }
  }

  return (
    <div className={cn('flex flex-col items-end gap-1', className)}>
      <button
        type="button"
        onClick={handleToggle}
        disabled={pending}
        aria-pressed={isFavorite}
        aria-label={ariaLabel}
        className="inline-flex disabled:opacity-60"
      >
        <Heart size={HEART_SIZE} strokeWidth={1.75} className={heartClass(isFavorite)} />
      </button>
      {hasError && (
        <span className="text-sm text-wine-500">{tr('favoriteError')}</span>
      )}
    </div>
  );
}
