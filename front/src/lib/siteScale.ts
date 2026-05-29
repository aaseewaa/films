/**
 * Глобальный масштаб UI (1 = прежний 16px root).
 * rem-классы Tailwind растут через font-size на html; граф и px — вручную.
 */
export const SITE_UI_SCALE = 1;

/** Рост раскладки графа — меньше NODE, чтобы узлы занимали больше экрана. */
export function graphSpreadScale(uiScale = SITE_UI_SCALE): number {
  return 1 + (uiScale - 1) * 0.5;
}
