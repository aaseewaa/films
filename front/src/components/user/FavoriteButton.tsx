import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addFavorite,
  checkFavorite,
  removeFavorite,
} from '@/api/userData';
import { useTranslation } from '@/hooks/useTranslation';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

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

  const labelClass =
    'text-lg sm:text-xl lg:text-2xl font-medium transition-colors whitespace-nowrap';

  if (!isAuthenticated) {
    return (
      <Link
        to="/auth/login"
        className={cn(labelClass, 'text-ink-50 hover:text-ink-300', className)}
      >
        {tr('addToFavorites')}
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
        className={cn(
          labelClass,
          'disabled:opacity-60',
          isFavorite ? 'text-wine-500 hover:text-wine-600' : 'text-ink-50 hover:text-ink-300',
        )}
      >
        {isFavorite ? tr('inFavorites') : tr('addToFavorites')}
      </button>
      {hasError && (
        <span className="text-sm text-wine-500">{tr('favoriteError')}</span>
      )}
    </div>
  );
}
