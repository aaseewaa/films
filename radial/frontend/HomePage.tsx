import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { getRadialGraph } from '@/api/graph';
import { pickRandomFavorite } from '@/lib/favoriteDirectors';

// ═══════════════════════════════════════════════
//  Геометрия — детерминированный radial layout
// ═══════════════════════════════════════════════

const POSITIONS_COUNT = 4;        // ровно 4 узла в круге
const RING_RADIUS = 280;           // расстояние от центра до узла (px)
const CENTER_SIZE = 200;           // диаметр центрального аватара
const NEIGHBOR_SIZE = 140;         // диаметр узла первого круга
const PLACEHOLDER_SIZE = 100;      // диаметр серой заглушки

/**
 * Координаты 4 позиций вокруг центра.
 * Углы: 12 / 3 / 6 / 9 часов — равномерное распределение.
 */
const POSITIONS: { angle: number; x: number; y: number }[] = (() => {
  const result: { angle: number; x: number; y: number }[] = [];
  for (let i = 0; i < POSITIONS_COUNT; i++) {
    // Начинаем с 12ч (-π/2) и идём по часовой
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / POSITIONS_COUNT;
    result.push({
      angle,
      x: Math.cos(angle) * RING_RADIUS,
      y: Math.sin(angle) * RING_RADIUS,
    });
  }
  return result;
})();

// ═══════════════════════════════════════════════
//  Компонент
// ═══════════════════════════════════════════════

export function HomePage() {
  const navigate = useNavigate();
  const [centerInfo] = useState(() => pickRandomFavorite());
  const [currentCenterId, setCurrentCenterId] = useState(centerInfo.id);
  const [hoverNodeId, setHoverNodeId] = useState<number | null>(null);

  // Загрузка центр + топ-4 соседей
  const { data, isLoading, error } = useQuery({
    queryKey: ['graph', 'radial', currentCenterId],
    queryFn: () => getRadialGraph(currentCenterId, POSITIONS_COUNT),
  });

  // Обработка ошибок
  if (error) {
    return (
      <div className="h-[calc(100vh-4rem)] flex items-center justify-center bg-graph-bg text-graph-text">
        <div className="text-center max-w-md px-6">
          <h2 className="font-serif text-2xl mb-2">Не удалось загрузить граф</h2>
          <p className="text-sm opacity-70 mb-2">
            Проверь что бэкенд запущен и доступен эндпоинт:
          </p>
          <code className="text-xs bg-graph-surface px-2 py-1 rounded">
            /api/graph/director/{currentCenterId}/radial
          </code>
          <p className="text-xs opacity-50 mt-3">
            Если эндпоинта нет — нужно применить патч бэка (см. инструкцию).
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] bg-graph-bg relative overflow-hidden">
      {/* Заголовок */}
      <div className="absolute top-6 left-6 z-10 pointer-events-none">
        <p className="font-serif text-graph-text text-3xl tracking-tight">
          Граф влияний
        </p>
        <p className="text-sm text-graph-text/60 mt-1.5">
          {data ? `Центр: ${data.center.name}` : 'Загружаем...'}
        </p>
        {data && (
          <p className="text-xs text-graph-text/40 mt-0.5">
            {data.neighbors.length} {plural(data.neighbors.length, 'связь', 'связи', 'связей')}
            {data.neighbors.length < POSITIONS_COUNT && (
              <span className="opacity-60">
                {' '}· {POSITIONS_COUNT - data.neighbors.length} {plural(POSITIONS_COUNT - data.neighbors.length, 'место заглушка', 'места заглушки', 'мест заглушек')}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Кнопка случайного режиссёра */}
      <div className="absolute top-6 right-6 z-10">
        <button
          onClick={() => {
            const next = pickRandomFavorite();
            setCurrentCenterId(next.id);
            setHoverNodeId(null);
          }}
          className="text-xs text-graph-text/60 hover:text-graph-text px-3 py-1.5 rounded border border-graph-edge hover:border-graph-text/40 transition-colors"
        >
          ↻ Случайный режиссёр
        </button>
      </div>

      {/* Подсказка снизу */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
        <p className="text-xs text-graph-text/40 tracking-wide">
          {hoverNodeId !== null
            ? 'Клик — сделать центром · двойной клик — открыть карточку'
            : 'Наведи курсор · кликни на узел чтобы перецентрировать'}
        </p>
      </div>

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-graph-text/60 text-sm">Подбираем режиссёров...</p>
        </div>
      )}

      {/* SVG со звёздной композицией */}
      {data && (
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="-500 -500 1000 1000"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Лучи-связи (рисуем СНАЧАЛА чтобы они были под узлами) */}
          {POSITIONS.map((pos, idx) => {
            const neighbor = data.neighbors[idx];
            const isPlaceholder = !neighbor;
            const targetSize = isPlaceholder ? PLACEHOLDER_SIZE : NEIGHBOR_SIZE;

            // Точка на границе центрального круга (с учётом radius)
            const startX = Math.cos(pos.angle) * (CENTER_SIZE / 2);
            const startY = Math.sin(pos.angle) * (CENTER_SIZE / 2);

            // Точка на границе целевого узла
            const endX = pos.x - Math.cos(pos.angle) * (targetSize / 2);
            const endY = pos.y - Math.sin(pos.angle) * (targetSize / 2);

            const isHighlighted =
              hoverNodeId === neighbor?.id ||
              hoverNodeId === data.center.id;

            return (
              <line
                key={`ray-${idx}`}
                x1={startX}
                y1={startY}
                x2={endX}
                y2={endY}
                stroke={
                  isPlaceholder
                    ? 'rgba(232, 223, 200, 0.08)'
                    : isHighlighted
                    ? 'rgba(239, 195, 88, 0.7)'
                    : 'rgba(232, 223, 200, 0.25)'
                }
                strokeWidth={isHighlighted ? 2 : 1}
                style={{ transition: 'stroke 0.3s, stroke-width 0.3s' }}
              />
            );
          })}

          {/* Центральный узел */}
          <NodeAvatar
            cx={0}
            cy={0}
            size={CENTER_SIZE}
            name={data.center.name}
            image={data.center.image}
            isCenter
            isHover={hoverNodeId === data.center.id}
            onHover={(h) => setHoverNodeId(h ? data.center.id : null)}
            onClick={() => navigate(`/director/${data.center.id}`)}
          />

          {/* Узлы первого круга + заглушки */}
          {POSITIONS.map((pos, idx) => {
            const neighbor = data.neighbors[idx];

            if (!neighbor) {
              // Серая заглушка
              return (
                <circle
                  key={`placeholder-${idx}`}
                  cx={pos.x}
                  cy={pos.y}
                  r={PLACEHOLDER_SIZE / 2}
                  fill="rgba(232, 223, 200, 0.06)"
                  stroke="rgba(232, 223, 200, 0.15)"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                />
              );
            }

            return (
              <NodeAvatar
                key={neighbor.id}
                cx={pos.x}
                cy={pos.y}
                size={NEIGHBOR_SIZE}
                name={neighbor.name}
                image={neighbor.image}
                isHover={hoverNodeId === neighbor.id}
                onHover={(h) => setHoverNodeId(h ? neighbor.id : null)}
                onClick={() => {
                  setCurrentCenterId(neighbor.id);
                  setHoverNodeId(null);
                }}
                onDoubleClick={() => navigate(`/director/${neighbor.id}`)}
              />
            );
          })}
        </svg>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
//  Подкомпонент: аватар (центр или сосед)
// ═══════════════════════════════════════════════

interface NodeAvatarProps {
  cx: number;
  cy: number;
  size: number;
  name: string;
  image?: string | null;
  isCenter?: boolean;
  isHover?: boolean;
  onHover: (hovering: boolean) => void;
  onClick: () => void;
  onDoubleClick?: () => void;
}

function NodeAvatar({
  cx,
  cy,
  size,
  name,
  image,
  isCenter,
  isHover,
  onHover,
  onClick,
  onDoubleClick,
}: NodeAvatarProps) {
  const radius = size / 2;
  const clipId = `clip-${cx}-${cy}-${size}`;
  const initial = name?.[0] ?? '?';

  // При hover увеличиваем чуть-чуть
  const scale = isHover ? 1.06 : 1;
  const strokeColor = isHover
    ? '#EFC358'  // золотой при hover
    : isCenter
    ? '#F6D77E'  // мягкий золотой для центра
    : 'rgba(232, 223, 200, 0.4)';
  const strokeWidth = isHover ? 4 : isCenter ? 3 : 1.5;

  return (
    <g
      style={{
        transform: `translate(${cx}px, ${cy}px) scale(${scale})`,
        transformOrigin: `${cx}px ${cy}px`,
        transformBox: 'view-box',
        transition: 'transform 0.25s ease-out',
        cursor: 'pointer',
      }}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
    >
      {/* Маска круга для фото */}
      <defs>
        <clipPath id={clipId}>
          <circle cx={0} cy={0} r={radius} />
        </clipPath>
      </defs>

      {/* Фоновый круг (если фото нет) */}
      <circle
        cx={0}
        cy={0}
        r={radius}
        fill={isCenter ? '#48473F' : '#34332D'}
      />

      {/* Фото */}
      {image && (
        <image
          x={-radius}
          y={-radius}
          width={size}
          height={size}
          href={image}
          preserveAspectRatio="xMidYMid slice"
          clipPath={`url(#${clipId})`}
        />
      )}

      {/* Инициал если фото нет */}
      {!image && (
        <text
          x={0}
          y={0}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#FAF6EE"
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: radius * 0.6,
            fontWeight: 600,
          }}
        >
          {initial}
        </text>
      )}

      {/* Обводка */}
      <circle
        cx={0}
        cy={0}
        r={radius}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        style={{ transition: 'stroke 0.25s, stroke-width 0.25s' }}
      />

      {/* Подпись имени (только если НЕ hover) */}
      {!isHover && (
        <g>
          {/* Подложка под текст для читаемости */}
          <rect
            x={-radius * 1.4}
            y={radius + 8}
            width={radius * 2.8}
            height={isCenter ? 36 : 28}
            fill="rgba(26, 24, 21, 0.85)"
            rx={3}
          />
          <text
            x={0}
            y={radius + (isCenter ? 30 : 24)}
            textAnchor="middle"
            fill="#FAF6EE"
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: isCenter ? 18 : 14,
              fontWeight: 500,
            }}
          >
            {truncate(name, isCenter ? 22 : 18)}
          </text>
        </g>
      )}
    </g>
  );
}

// ═══════════════════════════════════════════════
//  Утилиты
// ═══════════════════════════════════════════════

function truncate(s: string, max: number): string {
  return s.length <= max ? s : s.slice(0, max - 1) + '…';
}

function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}
