import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import {
  getRadialGraph,
  type RadialCenter,
  type RadialPerson,
  type RadialRing1Node,
} from '@/api/graph';
import { pickRandomFavorite } from '@/lib/favoriteDirectors';

const RING1_SLOTS = 4;
const RING2_SLOTS = 4;
const MAX_HISTORY = 3;

/**
 * Масштаб по скетчу: крупный центр, ring1 к краям экрана,
 * ring2/mini заполняют периферию (узлы и расстояния раздельно).
 */
const NODE_SCALE = 2.05;
const SPREAD_SCALE = 2.2;

const CENTER_SIZE = Math.round(200 * NODE_SCALE);
const RING1_SIZE = Math.round(120 * NODE_SCALE);
const CENTER_HOVER_SIZE = Math.round(108 * NODE_SCALE);
const RING2_ORBIT_SIZE = Math.round(54 * NODE_SCALE * 1.1);
const RING2_ORBIT_PLACEHOLDER = Math.round(38 * NODE_SCALE);
const NESTED_HOVER_ORBIT_SIZE = Math.round(44 * NODE_SCALE * 1.08);
const NESTED_HOVER_ORBIT_PLACEHOLDER = Math.round(30 * NODE_SCALE);
const PLACEHOLDER_SIZE = Math.round(88 * NODE_SCALE);

const RING1_RADIUS = Math.round(220 * SPREAD_SCALE);
const HOVER_INFLUENCER_RADIUS = Math.round(175 * SPREAD_SCALE);
const RING2_ORBIT_RADIUS = Math.round(96 * SPREAD_SCALE * 1.15);
const NESTED_HOVER_ORBIT_RADIUS = Math.round(80 * SPREAD_SCALE * 1.12);
const HOVER_PAN = 0.5;

/** viewBox по реальному радиусу кластера — без лишнего поля, граф заполняет экран. */
const GRAPH_VIEW_HALF = Math.round(
  RING1_RADIUS +
    RING2_ORBIT_RADIUS +
    NESTED_HOVER_ORBIT_RADIUS +
    RING2_ORBIT_SIZE,
);

const HISTORY_ORIGIN = { x: -400, y: 400 };
const HISTORY_SIZES = [56, 48, 40].map((s) => Math.round(s * NODE_SCALE));

const LABEL_SMALL_THRESHOLD = Math.round(90 * NODE_SCALE);

const PAN_TRANSITION = 'transform 0.55s cubic-bezier(0.25, 0.1, 0.25, 1)';
const NODE_TRANSITION = 'opacity 0.4s ease, transform 0.55s cubic-bezier(0.25, 0.1, 0.25, 1)';

const POSITIONS = Array.from({ length: RING1_SLOTS }, (_, i) => {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / RING1_SLOTS;
  return {
    angle,
    x: Math.cos(angle) * RING1_RADIUS,
    y: Math.sin(angle) * RING1_RADIUS,
  };
});

export function HomePage() {
  const navigate = useNavigate();
  const [currentCenterId, setCurrentCenterId] = useState(() => {
    const saved = sessionStorage.getItem('filmcine:current-center');
    if (saved) return parseInt(saved, 10);
    return pickRandomFavorite().id;
  });
  const [history, setHistory] = useState<RadialCenter[]>([]);
  /** Ring1 в режиме «героя» (остаётся, пока курсор в кластере). */
  const [expandedRing1Id, setExpandedRing1Id] = useState<number | null>(null);
  /** Наведение на узел внутри ring2 / hover-кольца. */
  const [nestedHover, setNestedHover] = useState<{
    id: number;
    x: number;
    y: number;
    heroRadius: number;
  } | null>(null);

  const clearHover = () => {
    setExpandedRing1Id(null);
    setNestedHover(null);
  };

  useEffect(() => {
    sessionStorage.setItem('filmcine:current-center', String(currentCenterId));
  }, [currentCenterId]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['graph', 'radial', currentCenterId, RING1_SLOTS, RING2_SLOTS],
    queryFn: () => getRadialGraph(currentCenterId, RING1_SLOTS, RING2_SLOTS),
  });

  const { data: expandedData } = useQuery({
    queryKey: ['graph', 'radial', 'expanded', expandedRing1Id, RING2_SLOTS],
    queryFn: () => getRadialGraph(expandedRing1Id!, RING1_SLOTS, RING2_SLOTS),
    enabled:
      expandedRing1Id !== null && expandedRing1Id !== currentCenterId,
  });

  const { data: nestedData } = useQuery({
    queryKey: ['graph', 'radial', 'nested', nestedHover?.id, RING2_SLOTS],
    queryFn: () => getRadialGraph(nestedHover!.id, RING1_SLOTS, RING2_SLOTS),
    enabled:
      nestedHover !== null &&
      nestedHover.id !== currentCenterId &&
      nestedHover.id !== expandedRing1Id,
  });

  const expandedSlotIdx = useMemo(() => {
    if (!expandedRing1Id || !data) return -1;
    return data.ring1.findIndex((n) => n.id === expandedRing1Id);
  }, [expandedRing1Id, data]);

  const ring1Expanded =
    expandedSlotIdx >= 0 && data !== undefined;

  const pan = ring1Expanded
    ? {
        x: -POSITIONS[expandedSlotIdx].x * HOVER_PAN,
        y: -POSITIONS[expandedSlotIdx].y * HOVER_PAN,
      }
    : { x: 0, y: 0 };

  const handleNestedNodeHover = (
    node: RadialPerson,
    anchor: { x: number; y: number },
    heroRadius: number,
    hovering: boolean,
  ) => {
    if (hovering) {
      setNestedHover({
        id: node.id,
        x: anchor.x,
        y: anchor.y,
        heroRadius,
      });
    } else {
      setNestedHover((prev) => (prev?.id === node.id ? null : prev));
    }
  };

  const promoteToCenter = (node: RadialPerson | RadialCenter) => {
    if (!data || node.id === currentCenterId) return;
    setHistory((h) => [...h.slice(-(MAX_HISTORY - 1)), { ...data.center }]);
    setCurrentCenterId(node.id);
    clearHover();
  };

  const goBackTo = (index: number) => {
    const target = history[index];
    if (!target) return;
    setHistory((h) => h.slice(0, index));
    setCurrentCenterId(target.id);
    clearHover();
  };

  if (error) {
    return (
      <div className="h-[calc(100vh-4.75rem)] lg:h-[calc(100vh-5rem)] flex items-center justify-center bg-header-bar text-white">
        <div className="text-center max-w-md px-6">
          <h2 className="font-serif text-2xl mb-2">Не удалось загрузить граф</h2>
          <code className="text-xs bg-graph-surface px-2 py-1 rounded">
            /api/graph/director/{currentCenterId}/radial
          </code>
        </div>
      </div>
    );
  }

  const focusNode = ring1Expanded ? data?.ring1[expandedSlotIdx] : null;
  const nestedFocusName =
    nestedHover && nestedData?.center.name
      ? nestedData.center.name
      : nestedHover
        ? data?.ring1.find((n) => n.id === nestedHover.id)?.name ??
          data?.ring1.flatMap((n) => n.ring2).find((n) => n.id === nestedHover.id)?.name
        : null;

  const nestedShownWithExpanded =
    ring1Expanded &&
    nestedHover !== null &&
    expandedData?.ring1.some((n) =>
      n.ring2.some((r) => r.id === nestedHover.id),
    );

  return (
    <div className="h-[calc(100vh-4.75rem)] lg:h-[calc(100vh-5rem)] bg-header-bar relative overflow-hidden">
      <HeaderPanel
        data={data}
        hoverActive={ring1Expanded}
        focusNode={focusNode}
        nestedFocusName={nestedFocusName}
      />

      <div className="absolute top-6 right-6 z-10">
        <button
          type="button"
          onClick={() => {
            setCurrentCenterId(pickRandomFavorite().id);
            setHistory([]);
            clearHover();
          }}
          className="text-xs text-white/60 hover:text-white px-3 py-1.5 rounded border border-white/25 hover:border-white/50 transition-colors"
        >
          ↻ Случайный режиссёр
        </button>
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none text-center">
        <p className="text-xs text-graph-text/40 tracking-wide">
          Наведи на вдохновителя — раскроется его круг · клик — новый центр · двойной клик — карточка
        </p>
        {history.length > 0 && (
          <p className="text-xs text-graph-text/30 mt-1">
            Слева внизу — откуда пришли ({history.length})
          </p>
        )}
      </div>

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="text-graph-text/60 text-sm">Подбираем режиссёров...</p>
        </div>
      )}

      {data && (
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox={`-${GRAPH_VIEW_HALF} -${GRAPH_VIEW_HALF} ${GRAPH_VIEW_HALF * 2} ${GRAPH_VIEW_HALF * 2}`}
          preserveAspectRatio="xMidYMid meet"
        >
          {renderHistory(history, goBackTo, (id) => navigate(`/director/${id}`))}

          <g
            style={{ transform: `translate(${pan.x}px, ${pan.y}px)`, transition: PAN_TRANSITION }}
            onMouseLeave={clearHover}
          >
            {POSITIONS.map((pos, idx) => {
              const node = data.ring1[idx];
              const isHover = ring1Expanded && idx === expandedSlotIdx;
              const centerR = ring1Expanded ? CENTER_HOVER_SIZE / 2 : CENTER_SIZE / 2;
              const endR = isHover
                ? CENTER_SIZE / 2
                : node
                  ? RING1_SIZE / 2
                  : PLACEHOLDER_SIZE / 2;
              const endX = pos.x - Math.cos(pos.angle) * endR;
              const endY = pos.y - Math.sin(pos.angle) * endR;

              return (
                <line
                  key={`ray-${idx}`}
                  x1={Math.cos(pos.angle) * centerR}
                  y1={Math.sin(pos.angle) * centerR}
                  x2={endX}
                  y2={endY}
                  stroke={
                    isHover
                      ? 'rgba(239, 195, 88, 0.7)'
                      : node
                        ? 'rgba(232, 223, 200, 0.22)'
                        : 'rgba(232, 223, 200, 0.1)'
                  }
                  strokeWidth={isHover ? 2 : 1}
                  style={{ transition: 'stroke 0.4s ease, stroke-width 0.4s ease' }}
                />
              );
            })}

            {POSITIONS.map((pos, idx) => {
              const node = data.ring1[idx];
              if (!node) return null;
              const isHover = ring1Expanded && idx === expandedSlotIdx;

              if (ring1Expanded) {
                if (!isHover) return null;
                if (!expandedData) return null;
                return renderInfluencersAroundAnchor({
                  keyPrefix: `hover-${node.id}`,
                  anchor: pos,
                  heroRadius: CENTER_SIZE / 2,
                  nodes: expandedData.ring1,
                  variant: 'hover',
                  autoExpandChildren: true,
                  highlightNodeId: nestedHover?.id,
                  onNestedNodeHover: handleNestedNodeHover,
                  onPromote: promoteToCenter,
                  onOpenCard: (id) => navigate(`/director/${id}`),
                });
              }

              return renderInfluencersAroundAnchor({
                keyPrefix: `r2-${node.id}`,
                anchor: pos,
                heroRadius: RING1_SIZE / 2,
                nodes: node.ring2,
                variant: 'compact',
                highlightNodeId: nestedHover?.id,
                onNestedNodeHover: handleNestedNodeHover,
                onPromote: promoteToCenter,
                onOpenCard: (id) => navigate(`/director/${id}`),
              });
            })}

            <NodeAvatar
              cx={0}
              cy={0}
              size={ring1Expanded ? CENTER_HOVER_SIZE : CENTER_SIZE}
              name={data.center.name}
              image={data.center.image}
              isCenter={!ring1Expanded}
              dimmed={ring1Expanded}
              onHover={() => clearHover()}
              onClick={() => {}}
              onDoubleClick={() => navigate(`/director/${data.center.id}`)}
            />

            {POSITIONS.map((pos, idx) => {
              const node = data.ring1[idx];
              if (!node) {
                return (
                  <PlaceholderRing
                    key={`ph1-${idx}`}
                    cx={pos.x}
                    cy={pos.y}
                    size={PLACEHOLDER_SIZE}
                    label="?"
                  />
                );
              }

              const isHover = ring1Expanded && idx === expandedSlotIdx;
              return (
                <NodeAvatar
                  key={node.id}
                  cx={pos.x}
                  cy={pos.y}
                  size={isHover ? CENTER_SIZE : RING1_SIZE}
                  name={node.name}
                  image={node.image}
                  isCenter={isHover}
                  dimmed={ring1Expanded && !isHover}
                  onHover={(h) => {
                    if (h) {
                      setExpandedRing1Id(node.id);
                      setNestedHover(null);
                    }
                  }}
                  onClick={() => promoteToCenter(node)}
                  onDoubleClick={() => navigate(`/director/${node.id}`)}
                />
              );
            })}

            {nestedHover &&
              nestedData &&
              nestedHover.id !== expandedRing1Id &&
              !nestedShownWithExpanded &&
              renderInfluencersAroundAnchor({
                keyPrefix: `nested-${nestedHover.id}`,
                anchor: {
                  x: nestedHover.x,
                  y: nestedHover.y,
                  angle: Math.atan2(nestedHover.y, nestedHover.x),
                },
                heroRadius: nestedHover.heroRadius,
                nodes: nestedData.ring1,
                variant: 'mini',
                onPromote: promoteToCenter,
                onOpenCard: (id) => navigate(`/director/${id}`),
              })}
          </g>
        </svg>
      )}
    </div>
  );
}

function HeaderPanel({
  data,
  hoverActive,
  focusNode,
  nestedFocusName,
}: {
  data: Awaited<ReturnType<typeof getRadialGraph>> | undefined;
  hoverActive: boolean;
  focusNode: { name: string } | null | undefined;
  nestedFocusName?: string | null;
}) {
  return (
    <div className="absolute top-6 left-6 z-10 pointer-events-none">
      <p className="font-serif text-white text-3xl tracking-tight">Граф влияний</p>
      <p className="text-sm text-white/60 mt-1.5">
        {data ? (
          hoverActive && focusNode ? (
            <>
              Смотрим: <span className="text-white">{focusNode.name}</span>
              {nestedFocusName && (
                <span className="opacity-70">
                  {' '}
                  → <span className="text-white">{nestedFocusName}</span>
                </span>
              )}
              <span className="opacity-50"> · центр: {data.center.name}</span>
            </>
          ) : (
            <>Центр: {data.center.name}</>
          )
        ) : (
          'Загружаем...'
        )}
      </p>
      {data && (
        <p className="text-xs text-white/40 mt-0.5">
          {data.ring1.length > 0 ? (
            <>
              {data.ring1.length}{' '}
              {plural(data.ring1.length, 'вдохновитель', 'вдохновителя', 'вдохновителей')}
            </>
          ) : (
            <span className="opacity-70">в БД пока нет связей — серые круги-заглушки</span>
          )}
          <span className="opacity-50"> · до {RING2_SLOTS} у каждого</span>
        </p>
      )}
    </div>
  );
}

function renderHistory(
  history: RadialCenter[],
  goBackTo: (index: number) => void,
  onOpenCard: (id: number) => void,
) {
  return history.map((crumb, idx) => {
    const size = HISTORY_SIZES[idx] ?? 36;
    const x = HISTORY_ORIGIN.x + idx * (size + 28);
    const y = HISTORY_ORIGIN.y;

    return (
      <g key={crumb.id}>
        <line
          x1={x + size / 2}
          y1={y}
          x2={idx < history.length - 1 ? HISTORY_ORIGIN.x + (idx + 1) * 52 : 0}
          y2={idx < history.length - 1 ? y : 0}
          stroke="rgba(239, 195, 88, 0.35)"
          strokeWidth={1}
          strokeDasharray={idx === history.length - 1 ? '4 6' : undefined}
        />
        <NodeAvatar
          cx={x}
          cy={y}
          size={size}
          name={crumb.name}
          image={crumb.image}
          dimmed
          onHover={() => {}}
          onClick={() => goBackTo(idx)}
          onDoubleClick={() => onOpenCard(crumb.id)}
        />
      </g>
    );
  });
}

const ORBIT_VARIANTS = {
  compact: {
    radius: RING2_ORBIT_RADIUS,
    nodeSize: RING2_ORBIT_SIZE,
    placeholderSize: RING2_ORBIT_PLACEHOLDER,
    rayStroke: 'rgba(232, 223, 200, 0.22)',
    rayWidth: 1,
  },
  hover: {
    radius: HOVER_INFLUENCER_RADIUS,
    nodeSize: RING1_SIZE,
    placeholderSize: PLACEHOLDER_SIZE,
    rayStroke: 'rgba(239, 195, 88, 0.45)',
    rayWidth: 1.5,
  },
  mini: {
    radius: NESTED_HOVER_ORBIT_RADIUS,
    nodeSize: NESTED_HOVER_ORBIT_SIZE,
    placeholderSize: NESTED_HOVER_ORBIT_PLACEHOLDER,
    rayStroke: 'rgba(239, 195, 88, 0.38)',
    rayWidth: 1,
  },
} as const;

type NestedNodeHoverHandler = (
  node: RadialPerson,
  anchor: { x: number; y: number },
  heroRadius: number,
  hovering: boolean,
) => void;

/** Вдохновители вокруг ring1: compact при открытии, hover при наведении. */
function renderInfluencersAroundAnchor(opts: {
  keyPrefix: string;
  anchor: { x: number; y: number; angle: number };
  heroRadius: number;
  nodes: RadialPerson[];
  variant: keyof typeof ORBIT_VARIANTS;
  /** Сразу рисовать ring2 у каждого узла (для hover на ring1). */
  autoExpandChildren?: boolean;
  highlightNodeId?: number;
  onNestedNodeHover?: NestedNodeHoverHandler;
  onPromote: (n: RadialPerson) => void;
  onOpenCard: (id: number) => void;
}) {
  const preset = ORBIT_VARIANTS[opts.variant];
  const slots = positionsAroundAnchorOuter(
    opts.anchor.x,
    opts.anchor.y,
    preset.radius,
    RING2_SLOTS,
  );

  return (
    <g key={opts.keyPrefix}>
      {slots.map((slot, idx) => {
        const node = opts.nodes[idx];
        const endR = node ? preset.nodeSize / 2 : preset.placeholderSize / 2;
        const endX = slot.x - Math.cos(slot.angle) * endR;
        const endY = slot.y - Math.sin(slot.angle) * endR;

        return (
          <line
            key={`${opts.keyPrefix}-ray-${idx}`}
            x1={opts.anchor.x + Math.cos(slot.angle) * opts.heroRadius}
            y1={opts.anchor.y + Math.sin(slot.angle) * opts.heroRadius}
            x2={endX}
            y2={endY}
            stroke={preset.rayStroke}
            strokeWidth={preset.rayWidth}
          />
        );
      })}

      {slots.map((slot, idx) => {
        const node = opts.nodes[idx];
        if (!node) {
          return (
            <PlaceholderRing
              key={`${opts.keyPrefix}-ph-${idx}`}
              cx={slot.x}
              cy={slot.y}
              size={preset.placeholderSize}
              small
            />
          );
        }

        return (
          <NodeAvatar
            key={`${opts.keyPrefix}-${node.id}`}
            cx={slot.x}
            cy={slot.y}
            size={preset.nodeSize}
            name={node.name}
            image={node.image}
            isCenter={opts.highlightNodeId === node.id}
            onHover={(h) => {
              if (opts.onNestedNodeHover) {
                opts.onNestedNodeHover(
                  node,
                  { x: slot.x, y: slot.y },
                  preset.nodeSize / 2,
                  h,
                );
              }
            }}
            onClick={() => opts.onPromote(node)}
            onDoubleClick={() => opts.onOpenCard(node.id)}
          />
        );
      })}

      {opts.autoExpandChildren &&
        slots.map((slot, idx) => {
          const parent = opts.nodes[idx] as RadialRing1Node | undefined;
          if (!parent?.ring2?.length) return null;

          return renderInfluencersAroundAnchor({
            keyPrefix: `${opts.keyPrefix}-r2-${parent.id}`,
            anchor: { x: slot.x, y: slot.y, angle: slot.angle },
            heroRadius: preset.nodeSize / 2,
            nodes: parent.ring2,
            variant: 'mini',
            highlightNodeId: opts.highlightNodeId,
            onNestedNodeHover: opts.onNestedNodeHover,
            onPromote: opts.onPromote,
            onOpenCard: opts.onOpenCard,
          });
        })}
    </g>
  );
}

/**
 * 4 слота по дуге «наружу» от центра графа — без узла, смотрящего в центр
 * (иначе при hover на нижнем ring1 всё слипается у Спилберга).
 */
function positionsAroundAnchorOuter(
  anchorX: number,
  anchorY: number,
  radius: number,
  slots: number,
): { x: number; y: number; angle: number }[] {
  const awayFromCenter =
    anchorX !== 0 || anchorY !== 0 ? Math.atan2(anchorY, anchorX) : -Math.PI / 2;
  // Полукруг «от центра графа», без слотов в сторону центра
  const span = Math.PI;
  const start = awayFromCenter - span / 2;

  return Array.from({ length: slots }, (_, i) => {
    const angle =
      slots === 1 ? awayFromCenter : start + (i / (slots - 1)) * span;
    return {
      angle,
      x: anchorX + Math.cos(angle) * radius,
      y: anchorY + Math.sin(angle) * radius,
    };
  });
}

function PlaceholderRing({
  cx,
  cy,
  size,
  label,
  small,
}: {
  cx: number;
  cy: number;
  size: number;
  label?: string;
  small?: boolean;
}) {
  const r = size / 2;
  return (
    <g>
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="rgba(232, 223, 200, 0.04)"
        stroke="rgba(232, 223, 200, 0.14)"
        strokeWidth={1}
        strokeDasharray="4 4"
      />
      {label && (
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="central"
          fill="rgba(232, 223, 200, 0.25)"
          style={{ fontSize: small ? 14 : 20, fontFamily: 'Inter, sans-serif' }}
        >
          {label}
        </text>
      )}
    </g>
  );
}

interface NodeAvatarProps {
  cx: number;
  cy: number;
  size: number;
  name: string;
  image?: string | null;
  isCenter?: boolean;
  dimmed?: boolean;
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
  dimmed,
  onHover,
  onClick,
  onDoubleClick,
}: NodeAvatarProps) {
  const radius = size / 2;
  const clipId = `clip-${cx}-${cy}-${size}-${name.slice(0, 3)}`;
  const initial = name?.[0] ?? '?';

  const labelAngle =
    cx === 0 && cy === 0 ? Math.PI / 2 : Math.atan2(cy, cx);
  const labelGap = isCenter ? Math.round(14 * NODE_SCALE / 2) : size < LABEL_SMALL_THRESHOLD ? 10 : 12;
  const labelR = radius + labelGap;
  const labelX = Math.cos(labelAngle) * labelR;
  const labelY = Math.sin(labelAngle) * labelR;

  return (
    <g
      style={{
        transform: `translate(${cx}px, ${cy}px)`,
        opacity: dimmed ? 0.4 : 1,
        transition: NODE_TRANSITION,
        cursor: 'pointer',
      }}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        onDoubleClick?.();
      }}
    >
      <defs>
        <clipPath id={clipId}>
          <circle cx={0} cy={0} r={radius} />
        </clipPath>
      </defs>

      <circle cx={0} cy={0} r={radius} fill={isCenter ? '#48473F' : '#34332D'} />

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

      {!image && (
        <text
          x={0}
          y={0}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#FAF6EE"
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: radius * 0.55,
            fontWeight: 600,
          }}
        >
          {initial}
        </text>
      )}

      <circle
        cx={0}
        cy={0}
        r={radius}
        fill="none"
        stroke={isCenter ? '#F6D77E' : 'rgba(232, 223, 200, 0.45)'}
        strokeWidth={isCenter ? 3 : 1.5}
      />

      <text
        x={labelX}
        y={labelY}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#FFFFFF"
        stroke="rgba(26, 24, 21, 0.75)"
        strokeWidth={2.5}
        paintOrder="stroke fill"
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: isCenter ? 18 : size < LABEL_SMALL_THRESHOLD ? 12 : 14,
          fontWeight: 500,
          pointerEvents: 'none',
        }}
      >
        {truncate(name, isCenter ? 26 : size < LABEL_SMALL_THRESHOLD ? 18 : 20)}
      </text>
    </g>
  );
}

function motionDiv({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={className}>{children}</div>;
}

function truncate(s: string, max: number): string {
  return s.length <= max ? s : `${s.slice(0, max - 1)}…`;
}

function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}
