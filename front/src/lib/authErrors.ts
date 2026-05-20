import axios from 'axios';

export function getAuthErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === 'object' && item !== null && 'msg' in item) {
            return String((item as { msg: string }).msg);
          }
          return String(item);
        })
        .join('. ');
    }
  }
  return 'Не удалось выполнить запрос. Попробуйте ещё раз.';
}
