import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Camera } from 'lucide-react';
import { uploadAvatar } from '@/api/auth';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';
import { validateAvatarFile } from '@/lib/avatarUpload';

interface AvatarUploadProps {
  avatarUrl?: string | null;
  displayName: string;
  size?: 'lg' | 'md';
}

export function AvatarUpload({
  avatarUrl,
  displayName,
  size = 'lg',
}: AvatarUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const setUser = useAuthStore((s) => s.setUser);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: uploadAvatar,
    onSuccess: (user) => {
      setUser(user);
      setPreview(null);
      setError(null);
    },
    onError: () => setError('Не удалось загрузить фото'),
  });

  const dim = size === 'lg' ? 'w-28 h-28 sm:w-32 sm:h-32' : 'w-20 h-20';
  const src = preview ?? avatarUrl ?? null;
  const initials = displayName
    .trim()
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    const validationError = validateAvatarFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setPreview(URL.createObjectURL(file));
    upload.mutate(file);
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={upload.isPending}
        className={cn(
          'relative rounded-full overflow-hidden border-2 border-[#3d4f5f]',
          'bg-[#2a3440] group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#40bcf4]',
          dim,
        )}
        aria-label="Загрузить фото профиля"
      >
        {src ? (
          <img src={src} alt="" className="w-full h-full object-cover" />
        ) : (
          <span className="flex items-center justify-center w-full h-full text-xl font-semibold text-[#9ab]">
            {initials || '?'}
          </span>
        )}
        <span
          className={cn(
            'absolute inset-0 flex items-center justify-center bg-black/50 opacity-0',
            'group-hover:opacity-100 transition-opacity',
          )}
        >
          <Camera className="text-white" size={size === 'lg' ? 28 : 20} />
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <p className="text-[0.6875rem] text-[#9ab]">Нажмите, чтобы загрузить с компьютера</p>
      {(error || upload.isPending) && (
        <p className={cn('text-xs', error ? 'text-[#e85d75]' : 'text-[#9ab]')}>
          {error ?? 'Загрузка…'}
        </p>
      )}
    </div>
  );
}
