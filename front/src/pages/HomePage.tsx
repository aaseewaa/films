import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import {
  getRadialGraph,
  type RadialCenter,
  type RadialPerson,
} from '@/api/graph';
import { pickRandomFavorite } from '@/lib/favoriteDirectors';

const RING1_SLOTS = 4;
const RING2_SLOTS = 4;
const MAX_HISTORY = 3;

const RING1_RADIUS = 220;
const CENTER_SIZE = 200;
const RING1_SIZE = 120;
const RING1_HOVER_SIZE = 168;
const CENTER_HOVER_SIZE = 108;
const RING2_SIZE = 72;
const PLACEHOLDER_SIZE = 88;
const RING2_FAN_DIST = 72;
const HOVER_PAN = 0.5;

const HISTORY_ORIGIN = { x: -400, y: 400 };
const HISTORY_SIZES = [56, 48, 40];

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
  const [hoverFocusId, setHoverFocusId] = useState<number | null>(null);

  useEffect(() => {
    sessionStorage.setItem('filmcine:current-center', String(currentCenterId));
  }, [currentCenterId]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['graph', 'radial', currentCenterId, RING1_SLOTS, RING2_SLOTS],
    queryFn: () => getRadialGraph(currentCenterId, RING1_SLOTS, RING2_SLOTS),
  });

  const { data: hoverData } = useQuery({
    queryKey: ['graph', 'radial', 'preview', hoverFocusId, RING2_SLOTS],
    queryFn: () => getRadialGraph(hoverFocusId!, RING1_SLOTS, RING2_SLOTS),
    enabled: hoverFocusId !== null && hoverFocusId !== currentCenterId,
  });

  const hoverSlotIdx = useMemo(() => {
    if (!hoverFocusId || !data) return -1;
    return data.ring1.findIndex((n) => n.id === hoverFocusId);
  }, [hoverFocusId, data]);

  const hoverActive =
    hoverSlotIdx >= 0 && data !== undefined && hoverFocusId !== data.center.id;

  const pan = hoverActive
    ? {
        x: -POSITIONS[hoverSlotIdx].x * HOVER_PAN,
        y: -POSITIONS[hoverSlotIdx].y * HOVER_PAN,
      }
    : { x: 0, y: 0 };

  const promoteToCenter = (node: RadialPerson | RadialCenter) => {
    if (!data || node.id === currentCenterId) return;
    setHistory((h) => [...h.slice(-(MAX_HISTORY - 1)), { ...data.center }]);
    setCurrentCenterId(node.id);
    setHoverFocusId(null);
  };

  const goBackTo = (index: number) => {
    const target = history[index];
    if (!target) return;
    setHistory((h) => h.slice(0, index));
    setCurrentCenterId(target.id);
    setHoverFocusId(null);
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

  const focusNode = hoverActive ? data?.ring1[hoverSlotIdx] : null;

  return (
    <div className="h-[calc(100vh-4.75rem)] lg:h-[calc(100vh-5rem)] bg-header-bar relative overflow-hidden">
      <headerPanel
        data={data}
        hoverActive={hoverActive}
        focusNode={focusNode}
      />

      <div className="absolute top-6 right-6 z-10">
        <button
          type="button"
          onClick={() => {
            setCurrentCenterId(pickRandomFavorite().id);
            setHistory([]);
            setHoverFocusId(null);
          }}
          className="text-xs text-white/60 hover:text-white px-3 py-1.5 rounded border border-white/25 hover:border-white/50 transition-colors"
        >
          ↻ Случайный режиссёр
        </button>
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-none text-center">
        <p className="text-xs text-graph-text/40 tracking-wide">
          Наведи на вдохновителя — граф сдвинется · клик — новый центр · двойной клик — карточка
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
          viewBox="-500 -500 1000 1000"
          preserveAspectRatio="xMidYMid meet"
        >
          {renderHistory(history, goBackTo, (id) => navigate(`/director/${id}`))}

          <g style={{ transform: `translate(${pan.x}px, ${pan.y}px)`, transition: PAN_TRANSITION }}>
            {POSITIONS.map((pos, idx) => {
              const node = data.ring1[idx];
              const isHover = hoverActive && idx === hoverSlotIdx;
              const centerR = hoverActive ? CENTER_HOVER_SIZE / 2 : CENTER_SIZE / 2;
              const endR = isHover
                ? RING1_HOVER_SIZE / 2
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
              const isHover = hoverActive && idx === hoverSlotIdx;
              const ring2Nodes = isHover && hoverData ? hoverData.ring1 : node.ring2;

              return renderRing2Fan({
                keyPrefix: `r2-${node.id}-${isHover ? 'h' : 'd'}`,
                anchor: pos,
                anchorRadius: isHover ? RING1_HOVER_SIZE / 2 : RING1_SIZE / 2,
                nodes: ring2Nodes,
                dimmed: hoverActive && !isHover,
                highlight: isHover,
                onPromote: promoteToCenter,
                onOpenCard: (id) => navigate(`/director/${id}`),
              });
            })}

            <NodeAvatar
              cx={0}
              cy={0}
              size={hoverActive ? CENTER_HOVER_SIZE : CENTER_SIZE}
              name={data.center.name}
              image={data.center.image}
              isCenter={!hoverActive}
              dimmed={hoverActive}
              onHover={() => setHoverFocusId(null)}
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

              const isHover = hoverActive && idx === hoverSlotIdx;
              return (
                <NodeAvatar
                  key={node.id}
                  cx={pos.x}
                  cy={pos.y}
                  size={isHover ? RING1_HOVER_SIZE : RING1_SIZE}
                  name={node.name}
                  image={node.image}
                  isCenter={isHover}
                  dimmed={hoverActive && !isHover}
                  onHover={(h) => setHoverFocusId(h ? node.id : null)}
                  onClick={() => promoteToCenter(node)}
                  onDoubleClick={() => navigate(`/director/${node.id}`)}
                />
              );
            })}
          </g>
        </svg>
      )}
    </div>
  );
}

function headerPanel({
  data,
  hoverActive,
  focusNode,
}: {
  data: Awaited<ReturnType<typeof getRadialGraph>> | undefined;
  hoverActive: boolean;
  focusNode: { name: string } | null | undefined;
}) {
  return (
    <div className="absolute top-6 left-6 z-10 pointer-events-none">
      <p className="font-serif text-white text-3xl tracking-tight">Граф влияний</p>
      <p className="text-sm text-white/60 mt-1.5">
        {data ? (
          hoverActive && focusNode ? (
            <>
              Смотрим: <span className="text-white">{focusNode.name}</span>
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

function renderRing2Fan(opts: {
  keyPrefix: string;
  anchor: { x: number; y: number; angle: number };
  anchorRadius: number;
  nodes: RadialPerson[];
  dimmed?: boolean;
  highlight?: boolean;
  onPromote: (n: RadialPerson) => void;
  onOpenCard: (id: number) => void;
}) {
  const positions = fanPositions(opts.anchor, opts.anchorRadius, RING2_SLOTS);
  const opacity = opts.dimmed ? 0.28 : 1;

  return (
    <g style={{ opacity, transition: 'opacity 0.4s ease' }}>
      {positions.map((p, slotIdx) => {
        const node = opts.nodes[slotIdx];
        if (!node) {
          return (
            <PlaceholderRing
              key={`${opts.keyPrefix}-ph-${slotIdx}`}
              cx={p.x}
              cy={p.y}
              size={RING2_SIZE}
              small
            />
          );
        }

        return (
          <g key={`${opts.keyPrefix}-${node.id}`}>
            <line
              x1={opts.anchor.x + Math.cos(opts.anchor.angle) * opts.anchorRadius * 0.35}
              y1={opts.anchor.y + Math.sin(opts.anchor.angle) * opts.anchorRadius * 0.35}
              x2={p.x}
              y2={p.y}
              stroke={
                opts.highlight
                  ? 'rgba(239, 195, 88, 0.35)'
                  : 'rgba(232, 223, 200, 0.14)'
              }
              strokeWidth={1}
            />
            <NodeAvatar
              cx={p.x}
              cy={p.y}
              size={RING2_SIZE}
              name={node.name}
              image={node.image}
              onHover={() => {}}
              onClick={() => opts.onPromote(node)}
              onDoubleClick={() => opts.onOpenCard(node.id)}
            />
          </g>
        );
      })}
    </g>
  );
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

function fanPositions(
  anchor: { x: number; y: number; angle: number },
  anchorRadius: number,
  slots: number,
): { x: number; y: number }[] {
  const outward = { x: Math.cos(anchor.angle), y: Math.sin(anchor.angle) };
  const perp = { x: -outward.y, y: outward.x };
  const baseX = anchor.x + outward.x * (anchorRadius + RING2_FAN_DIST);
  const baseY = anchor.y + outward.y * (anchorRadius + RING2_FAN_DIST);

  return Array.from({ length: slots }, (_, i) => {
    const t = slots === 1 ? 0 : (i - (slots - 1) / 2) * 0.38;
    return {
      x: baseX + perp.x * t * 58,
      y: baseY + perp.y * t * 58,
    };
  });
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

      <rect
        x={-radius * 1.3}
        y={radius + 6}
        width={radius * 2.6}
        height={isCenter ? 30 : 22}
        fill="rgba(26, 24, 21, 0.88)"
        rx={3}
      />
      <text
        x={0}
        y={radius + (isCenter ? 24 : 18)}
        textAnchor="middle"
        fill="#FAF6EE"
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: isCenter ? 15 : 11,
          fontWeight: 500,
        }}
      >
        {truncate(name, isCenter ? 20 : 14)}
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
