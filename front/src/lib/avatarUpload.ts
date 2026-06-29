/** Должен совпадать с AVATAR_MAX_BYTES в backend/.env */
export const AVATAR_MAX_BYTES =
  Number(import.meta.env.VITE_AVATAR_MAX_BYTES) || 10 * 1024 * 1024;

export function avatarMaxSizeLabel(): string {
  const mb = AVATAR_MAX_BYTES / (1024 * 1024);
  return Number.isInteger(mb) ? `${mb} MB` : `${mb.toFixed(1)} MB`;
}

export function validateAvatarFile(file: File): string | null {
  if (!file.type.startsWith('image/')) {
    return 'Выберите изображение';
  }
  if (file.size > AVATAR_MAX_BYTES) {
    return `Файл больше ${avatarMaxSizeLabel()}`;
  }
  return null;
}
