import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Camera } from 'lucide-react';
import { uploadAvatar } from '@/api/auth';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/lib/utils';

interface ProfileAvatarHeroProps {
  avatarUrl?: string | null;
  displayName: string;
}

/** Портрет в правой колонке hero — как фото режиссёра, с загрузкой по клику. */
export function ProfileAvatarHero({ avatarUrl, displayName }: ProfileAvatarHeroProps) {
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
    if (!file.type.startsWith('image/')) {
      setError('Выберите изображение');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('Файл больше 2 MB');
      return;
    }
    setPreview(URL.createObjectURL(file));
    upload.mutate(file);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={upload.isPending}
        className="absolute inset-0 w-full h-full group focus:outline-none focus-visible:ring-2 focus-visible:ring-wine-500 focus-visible:ring-inset"
        aria-label="Загрузить фото профиля"
      >
        {src ? (
          <img
            src={src}
            alt={displayName}
            className="absolute inset-0 w-full h-full object-cover object-[center_12%]"
          />
        ) : (
          <div
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-cream-300"
            aria-hidden
          >
            <span className="font-serif text-6xl sm:text-7xl text-ink-50/40">
              {initials || '?'}
            </span>
            <span className="text-sm text-ink-50 px-4 text-center">
              Нажмите, чтобы загрузить фото
            </span>
          </div>
        )}
        <span
          className={cn(
            'absolute inset-0 flex flex-col items-center justify-center gap-2',
            'bg-ink-500/40 opacity-0 group-hover:opacity-100 transition-opacity',
          )}
        >
          <Camera className="text-white" size={40} />
          <span className="text-sm text-white font-medium">Загрузить с компьютера</span>
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {(error || upload.isPending) && (
        <p
          className={cn(
            'absolute bottom-4 left-4 right-4 text-center text-sm px-3 py-2 rounded-sm',
            error ? 'bg-wine-500/90 text-white' : 'bg-ink-500/80 text-white',
          )}
        >
          {error ?? 'Загрузка…'}
        </p>
      )}
    </>
  );
}
