import { TIFFANY } from '@/lib/homeGraphLayout';

interface GraphHeaderCaptionProps {
  centerLine: React.ReactNode;
  statsLine: React.ReactNode;
  loading: boolean;
}

/** Подпись графа влияний — справа от логотипа FMW */
export function GraphHeaderCaption({
  centerLine,
  statsLine,
  loading,
}: GraphHeaderCaptionProps) {
  return (
    <div className="hidden md:block min-w-0 pl-1 lg:pl-2 border-l border-ink-50/15 ml-1 lg:ml-2 max-w-[min(100%,22rem)] lg:max-w-[min(100%,28rem)]">
      <p
        className="font-serif text-[clamp(1.1rem,1.8vw,1.65rem)] font-bold tracking-tight leading-none"
        style={{ color: TIFFANY }}
      >
        Граф влияний
      </p>
      <p className="text-[clamp(0.75rem,1.1vw,0.95rem)] text-ink-500 mt-1 leading-snug">
        {loading ? 'Загружаем...' : centerLine}
      </p>
      {!loading && statsLine && (
        <p className="text-[clamp(0.7rem,1vw,0.875rem)] text-ink-500 mt-0.5 leading-snug">
          {statsLine}
        </p>
      )}
    </div>
  );
}
