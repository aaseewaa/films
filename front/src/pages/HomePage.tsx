import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import {
  getGraphCenters,
  getRadialGraph,
  type RadialCenter,
  type RadialPerson,
  type RadialRing1Node,
} from '@/api/graph';
import { pickRandomCenterId } from '@/lib/favoriteDirectors';
import {
  CENTER_HOVER_SIZE,
  CENTER_SIZE,
  GRAPH_VIEW_HALF,
  HISTORY_ORIGIN,
  HISTORY_SIZES,
  HOVER_CLEAR_MS,
  HOVER_INFLUENCER_RADIUS,
  HOVER_PAN,
  LABEL_SMALL_THRESHOLD,
  MAX_HISTORY,
  NESTED_HOVER_ORBIT_PLACEHOLDER,
  NESTED_HOVER_ORBIT_RADIUS,
  NESTED_HOVER_ORBIT_SIZE,
  NODE_TRANSITION,
  PAN_TRANSITION,
  PLACEHOLDER_SIZE,
  ring1LayoutPositions,
  RING1_SIZE,
  RING1_SLOTS,
  RING2_ORBIT_PLACEHOLDER,
  RING2_ORBIT_RADIUS,
  RING2_ORBIT_SIZE,
  RING2_SLOTS,
  NODE_SCALE,
  SINGLE_CLICK_DELAY_MS,
  TIFFANY,
} from '@/lib/homeGraphLayout';
import { SITE_GUTTER_CLASS } from '@/lib/siteGutter';
import { SITE_UI_SCALE } from '@/lib/siteScale';
import { useSiteLang } from '@/lib/siteLang';
import { cn } from '@/lib/utils';

export function HomePage() {
  const navigate = useNavigate();
  const lang = useSiteLang();
  const [currentCenterId, setCurrentCenterId] = useState<number | null>(null);

  const { data: centersData, isLoading: centersLoading } = useQuery({
    queryKey: ['graph', 'centers', lang],
    queryFn: () => getGraphCenters(80, 2),
    staleTime: 5 * 60_000,
  });
  const centerPool = useMemo(
    () => centersData?.centers ?? [],
    [centersData?.centers],
  );

  useEffect(() => {
    if (centersLoading || currentCenterId !== null) return;
    const saved = sessionStorage.getItem('filmcine:current-center');
    const savedId = saved ? parseInt(saved, 10) : NaN;
    if (centerPool.length > 0 && centerPool.some((c) => c.id === savedId)) {
      setCurrentCenterId(savedId);
      return;
    }
    if (centerPool.length > 0) {
      setCurrentCenterId(pickRandomCenterId(centerPool));
      return;
    }
    setCurrentCenterId(pickRandomCenterId([]));
  }, [centersLoading, centerPool, currentCenterId]);
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

  const hoverClearTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [graphFillScale, setGraphFillScale] = useState(1);

  useEffect(() => {
    const updateGraphFillScale = () => {
      const w = window.innerWidth;
      const h = Math.max(320, window.innerHeight - 104);
      const fitted = Math.min(w, h);
      const scale =
        w > h * 1.15 ? (w * 0.78) / fitted : (h * 0.82) / fitted;
      setGraphFillScale(Math.min(1.85, Math.max(1, scale)));
    };
    updateGraphFillScale();
    window.addEventListener('resize', updateGraphFillScale);
    return () => window.removeEventListener('resize', updateGraphFillScale);
  }, []);

  const clearHover = useCallback(() => {
    setExpandedRing1Id(null);
    setNestedHover(null);
  }, []);

  const cancelScheduledClearHover = useCallback(() => {
    if (hoverClearTimer.current !== null) {
      clearTimeout(hoverClearTimer.current);
      hoverClearTimer.current = null;
    }
  }, []);

  const scheduleClearHover = useCallback(() => {
    cancelScheduledClearHover();
    hoverClearTimer.current = setTimeout(() => {
      hoverClearTimer.current = null;
      clearHover();
    }, HOVER_CLEAR_MS);
  }, [cancelScheduledClearHover, clearHover]);

  useEffect(() => () => cancelScheduledClearHover(), [cancelScheduledClearHover]);

  useEffect(() => {
    if (currentCenterId !== null) {
      sessionStorage.setItem('filmcine:current-center', String(currentCenterId));
    }
  }, [currentCenterId]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['graph', 'radial', currentCenterId, RING1_SLOTS, RING2_SLOTS, lang],
    queryFn: () => getRadialGraph(currentCenterId!, RING1_SLOTS, RING2_SLOTS),
    enabled: currentCenterId !== null,
  });

  const { data: expandedData } = useQuery({
    queryKey: ['graph', 'radial', 'expanded', expandedRing1Id, RING2_SLOTS, lang],
    queryFn: () => getRadialGraph(expandedRing1Id!, RING1_SLOTS, RING2_SLOTS),
    enabled:
      expandedRing1Id !== null && expandedRing1Id !== currentCenterId,
  });

  const { data: nestedData } = useQuery({
    queryKey: ['graph', 'radial', 'nested', nestedHover?.id, RING2_SLOTS, lang],
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

  const ring1Positions = useMemo(
    () => (data ? ring1LayoutPositions(data.ring1.length) : []),
    [data],
  );

  const ring1Expanded =
    expandedSlotIdx >= 0 && data !== undefined;

  const pan = ring1Expanded
    ? {
        x: -ring1Positions[expandedSlotIdx].x * HOVER_PAN,
        y: -ring1Positions[expandedSlotIdx].y * HOVER_PAN,
      }
    : { x: 0, y: 0 };

  const handleNestedNodeHover = (
    node: RadialPerson,
    anchor: { x: number; y: number },
    heroRadius: number,
    hovering: boolean,
  ) => {
    if (hovering) {
      cancelScheduledClearHover();
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

  if (currentCenterId === null || (centersLoading && !data)) {
    return (
      <div className="h-[calc(100vh-5.75rem)] sm:h-[calc(100vh-6rem)] lg:h-[calc(100vh-6.5rem)] flex items-center justify-center bg-site-bg">
        <p className="text-graph-text/60 text-sm">Подбираем режиссёров...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[calc(100vh-5.75rem)] sm:h-[calc(100vh-6rem)] lg:h-[calc(100vh-6.5rem)] flex items-center justify-center bg-site-bg text-ink-400">
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
    <div className="h-[calc(100vh-5.75rem)] sm:h-[calc(100vh-6rem)] lg:h-[calc(100vh-6.5rem)] bg-site-bg relative overflow-hidden">
      <GraphTopBar
        data={data}
        hoverActive={ring1Expanded}
        focusNode={focusNode}
        nestedFocusName={nestedFocusName}
        onRandomDirector={() => {
          const pool = centerPool.length > 0 ? centerPool : [];
          setCurrentCenterId(pickRandomCenterId(pool));
          setHistory([]);
          clearHover();
        }}
        randomDisabled={centersLoading && centerPool.length === 0}
      />

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none text-center">
        <p className="text-sm text-graph-text/50 tracking-wide">
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
          <g transform={`scale(${graphFillScale})`}>
          {renderHistory(history, goBackTo, (id) => navigate(`/director/${id}`))}

          <g
            style={{ transform: `translate(${pan.x}px, ${pan.y}px)`, transition: PAN_TRANSITION }}
            onMouseEnter={cancelScheduledClearHover}
            onMouseLeave={scheduleClearHover}
          >
            {ring1Expanded && expandedSlotIdx >= 0 && (
              <circle
                cx={ring1Positions[expandedSlotIdx].x}
                cy={ring1Positions[expandedSlotIdx].y}
                r={
                  CENTER_SIZE / 2 +
                  HOVER_INFLUENCER_RADIUS +
                  NESTED_HOVER_ORBIT_RADIUS +
                  RING1_SIZE / 2
                }
                fill="transparent"
                style={{ pointerEvents: 'all' }}
                onMouseEnter={cancelScheduledClearHover}
              />
            )}

            {ring1Positions.map((pos, idx) => {
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

            <NodeAvatar
              cx={0}
              cy={0}
              size={ring1Expanded ? CENTER_HOVER_SIZE : CENTER_SIZE}
              name={data.center.name}
              image={data.center.image}
              isCenter={!ring1Expanded}
              dimmed={ring1Expanded}
              pointerEvents={ring1Expanded ? 'none' : 'auto'}
              onHover={() => {}}
              onClick={() => {}}
              onDoubleClick={() => navigate(`/director/${data.center.id}`)}
            />

            {ring1Positions.map((pos, idx) => {
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
                  pointerEvents={ring1Expanded && !isHover ? 'none' : 'auto'}
                  onHover={(h) => {
                    if (h) {
                      cancelScheduledClearHover();
                      setExpandedRing1Id(node.id);
                      setNestedHover(null);
                    }
                  }}
                  onClick={() => promoteToCenter(node)}
                  onDoubleClick={() => navigate(`/director/${node.id}`)}
                />
              );
            })}

            {ring1Positions.map((pos, idx) => {
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
          </g>
        </svg>
      )}
    </div>
  );
}

function GraphTopBar({
  data,
  hoverActive,
  focusNode,
  nestedFocusName,
  onRandomDirector,
  randomDisabled,
}: {
  data: Awaited<ReturnType<typeof getRadialGraph>> | undefined;
  hoverActive: boolean;
  focusNode: { name: string } | null | undefined;
  nestedFocusName?: string | null;
  onRandomDirector: () => void;
  randomDisabled: boolean;
}) {
  return (
    <div
      className={cn(
        'absolute top-6 left-0 right-0 z-10',
        SITE_GUTTER_CLASS,
      )}
    >
      <div className="mx-auto flex w-full max-w-page items-start justify-between gap-4 sm:gap-6">
        <div className="pointer-events-none min-w-0">
          <p
            className="font-serif text-[clamp(1.75rem,3.5vw,3.25rem)] font-bold tracking-tight leading-none"
            style={{ color: TIFFANY }}
          >
            Граф влияний
          </p>
          <p className="text-[clamp(0.95rem,1.6vw,1.375rem)] text-ink-500 mt-1.5">
            {data ? (
              hoverActive && focusNode ? (
                <>
                  Смотрим: <span className="font-medium">{focusNode.name}</span>
                  {nestedFocusName && (
                    <>
                      {' '}
                      → <span className="font-medium">{nestedFocusName}</span>
                    </>
                  )}
                  <span className="text-ink-300"> · центр: {data.center.name}</span>
                </>
              ) : (
                <>Центр: {data.center.name}</>
              )
            ) : (
              'Загружаем...'
            )}
          </p>
          {data && (
            <p className="text-[clamp(0.875rem,1.4vw,1.25rem)] text-ink-500 mt-0.5">
              {data.ring1.length > 0 ? (
                <>
                  {data.ring1.length}{' '}
                  {plural(data.ring1.length, 'вдохновитель', 'вдохновителя', 'вдохновителей')}
                </>
              ) : (
                'в БД пока нет связей — серые круги-заглушки'
              )}
              <span> · до {RING2_SLOTS} у каждого</span>
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={onRandomDirector}
          disabled={randomDisabled}
          className={cn(
            'shrink-0 text-base sm:text-lg font-medium leading-tight',
            'text-[#0ABAB5] px-4 py-2 rounded border border-[#0ABAB5]/40',
            'hover:border-[#0ABAB5] transition-colors',
            'disabled:opacity-40 disabled:cursor-not-allowed',
          )}
        >
          ↻ Случайный режиссёр
        </button>
      </div>
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
          style={{
            fontSize: Math.round((small ? 14 : 20) * SITE_UI_SCALE),
            fontFamily: 'Inter, sans-serif',
          }}
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
  pointerEvents?: 'auto' | 'none';
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
  pointerEvents = 'auto',
  onHover,
  onClick,
  onDoubleClick,
}: NodeAvatarProps) {
  const radius = size / 2;
  const clipId = `clip-${cx}-${cy}-${size}-${name.slice(0, 3)}`;
  const initials = (name || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase() || '?';
  const singleClickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (singleClickTimer.current !== null) {
        clearTimeout(singleClickTimer.current);
      }
    },
    [],
  );

  const labelGap = isCenter
    ? Math.round((14 * NODE_SCALE) / 2)
    : size < LABEL_SMALL_THRESHOLD
      ? 10
      : 12;
  const labelY = radius + labelGap;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (pointerEvents === 'none') return;
    if (singleClickTimer.current !== null) {
      clearTimeout(singleClickTimer.current);
    }
    singleClickTimer.current = setTimeout(() => {
      singleClickTimer.current = null;
      onClick();
    }, SINGLE_CLICK_DELAY_MS);
  };

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (pointerEvents === 'none') return;
    if (singleClickTimer.current !== null) {
      clearTimeout(singleClickTimer.current);
      singleClickTimer.current = null;
    }
    onDoubleClick?.();
  };

  return (
    <g
      style={{
        transform: `translate(${cx}px, ${cy}px)`,
        opacity: dimmed ? 0.4 : 1,
        transition: NODE_TRANSITION,
        cursor: pointerEvents === 'none' ? 'default' : 'pointer',
        pointerEvents,
      }}
      onMouseEnter={() => {
        if (pointerEvents === 'none') return;
        onHover(true);
      }}
      onMouseLeave={() => {
        if (pointerEvents === 'none') return;
        onHover(false);
      }}
      onClick={handleClick}
      onDoubleClick={onDoubleClick ? handleDoubleClick : undefined}
    >
      <defs>
        <clipPath id={clipId}>
          <circle cx={0} cy={0} r={radius} />
        </clipPath>
      </defs>

      <circle cx={0} cy={0} r={radius} fill={isCenter ? '#48473F' : '#34332D'} />

      {!image && (
        <circle
          cx={0}
          cy={0}
          r={radius * 0.92}
          fill="rgba(246, 215, 126, 0.12)"
        />
      )}

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
          {initials}
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
        x={0}
        y={labelY}
        textAnchor="middle"
        dominantBaseline="hanging"
        fill="#1A1815"
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: Math.round(
            (isCenter ? 20 : size < LABEL_SMALL_THRESHOLD ? 14 : 16) * SITE_UI_SCALE,
          ),
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
