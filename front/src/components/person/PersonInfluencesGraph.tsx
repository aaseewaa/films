import { useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getRadialGraph, type RadialPerson } from '@/api/graph';
import { useTranslation } from '@/hooks/useTranslation';
import type { PersonHeroPlate } from '@/lib/personHeroTheme';
import { graphSpreadScale, SITE_UI_SCALE } from '@/lib/siteScale';
import { useSiteLang } from '@/lib/siteLang';
import { cn } from '@/lib/utils';

const RING1_SLOTS = 6;
const RING2_SLOTS = 4;
const NODE_SCALE = 1.85 * SITE_UI_SCALE;
const SPREAD_SCALE = 2 * graphSpreadScale();

const CENTER_SIZE = Math.round(180 * NODE_SCALE);
const RING1_SIZE = Math.round(108 * NODE_SCALE);
const RING2_SIZE = Math.round(52 * NODE_SCALE);
const PLACEHOLDER_SIZE = Math.round(72 * NODE_SCALE);
const RING1_RADIUS = Math.round(200 * SPREAD_SCALE);
const RING2_RADIUS = Math.round(88 * SPREAD_SCALE);
const GRAPH_VIEW_HALF = Math.round((RING1_RADIUS + RING2_RADIUS + RING2_SIZE) * 0.9);
const LABEL_SMALL = Math.round(80 * NODE_SCALE);

const POSITIONS = Array.from({ length: RING1_SLOTS }, (_, i) => {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / RING1_SLOTS;
  return {
    angle,
    x: Math.cos(angle) * RING1_RADIUS,
    y: Math.sin(angle) * RING1_RADIUS,
  };
});

interface PersonInfluencesGraphProps {
  directorId: number;
  directorName: string;
  plate: PersonHeroPlate;
}

export function PersonInfluencesGraph({
  directorId,
  directorName,
  plate,
}: PersonInfluencesGraphProps) {
  const navigate = useNavigate();
  const tr = useTranslation();
  const lang = useSiteLang();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['graph', 'radial', 'person-page', directorId, lang],
    queryFn: () => getRadialGraph(directorId, RING1_SLOTS, RING2_SLOTS),
    staleTime: 60_000,
  });

  const theme = plate.textLight ? 'on-dark' : 'on-light';
  const colors =
    theme === 'on-light'
      ? {
          ray: 'rgba(66, 47, 51, 0.22)',
          rayActive: 'rgba(66, 47, 51, 0.45)',
          hint: 'text-ink-300/70',
          title: 'text-ink-500',
          sub: 'text-ink-50',
        }
      : {
          ray: 'rgba(255, 255, 255, 0.22)',
          rayActive: 'rgba(255, 255, 255, 0.55)',
          hint: 'text-white/55',
          title: 'text-white',
          sub: 'text-white/65',
        };

  const scheduleClear = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    hoverTimer.current = setTimeout(() => setExpandedId(null), 140);
  }, []);

  const cancelClear = useCallback(() => {
    if (hoverTimer.current) {
      clearTimeout(hoverTimer.current);
      hoverTimer.current = null;
    }
  }, []);

  const expandedIdx =
    expandedId != null && data
      ? data.ring1.findIndex((n) => n.id === expandedId)
      : -1;

  return (
    <div
      className="relative overflow-hidden rounded-sm min-h-[min(85vh,920px)]"
      style={{ backgroundColor: plate.bg }}
    >
      <div className="absolute top-5 left-5 sm:top-6 sm:left-8 z-10 pointer-events-none max-w-lg">
        <p className={cn('font-serif text-2xl sm:text-3xl', colors.title)}>
          {tr('personInfluencesTitle')}
        </p>
        <p className={cn('text-sm sm:text-base mt-1', colors.sub)}>
          {tr('personInfluencesCenter')}: {directorName}
          {data && data.ring1.length > 0 && (
            <span>
              {' '}
              · {data.ring1.length} {tr('personInfluencesInMap')}
            </span>
          )}
        </p>
        <p className={cn('text-xs mt-1', colors.hint)}>{tr('personInfluencesHint')}</p>
      </div>

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className={cn('text-sm', colors.sub)}>{tr('personGraphLoading')}</p>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center px-6 text-center">
          <p className={cn('text-sm', colors.sub)}>{tr('personGraphError')}</p>
        </div>
      )}

      {data && (
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox={`-${GRAPH_VIEW_HALF} -${GRAPH_VIEW_HALF} ${GRAPH_VIEW_HALF * 2} ${GRAPH_VIEW_HALF * 2}`}
          preserveAspectRatio="xMidYMid meet"
          onMouseEnter={cancelClear}
          onMouseLeave={scheduleClear}
        >
          <g>
            {POSITIONS.map((pos, idx) => {
              const node = data.ring1[idx];
              const active = expandedIdx === idx;
              const endR = node ? (active ? CENTER_SIZE / 2 : RING1_SIZE / 2) : PLACEHOLDER_SIZE / 2;
              return (
                <line
                  key={`ray-${idx}`}
                  x1={Math.cos(pos.angle) * (CENTER_SIZE / 2)}
                  y1={Math.sin(pos.angle) * (CENTER_SIZE / 2)}
                  x2={pos.x - Math.cos(pos.angle) * endR}
                  y2={pos.y - Math.sin(pos.angle) * endR}
                  stroke={active ? colors.rayActive : colors.ray}
                  strokeWidth={active ? 2 : 1}
                />
              );
            })}

            <GraphNode
              cx={0}
              cy={0}
              size={expandedIdx >= 0 ? Math.round(CENTER_SIZE * 0.88) : CENTER_SIZE}
              name={data.center.name}
              image={data.center.image}
              isCenter
              theme={theme}
              dimmed={expandedIdx >= 0}
              onOpen={() => navigate(`/director/${data.center.id}`)}
            />

            {POSITIONS.map((pos, idx) => {
              const node = data.ring1[idx];
              if (!node) {
                return (
                  <circle
                    key={`ph-${idx}`}
                    cx={pos.x}
                    cy={pos.y}
                    r={PLACEHOLDER_SIZE / 2}
                    fill="transparent"
                    stroke={colors.ray}
                    strokeWidth={1}
                    strokeDasharray="4 4"
                  />
                );
              }
              const active = expandedIdx === idx;
              return (
                <g key={node.id}>
                  <GraphNode
                    cx={pos.x}
                    cy={pos.y}
                    size={active ? CENTER_SIZE : RING1_SIZE}
                    name={node.name}
                    image={node.image}
                    isCenter={active}
                    theme={theme}
                    dimmed={expandedIdx >= 0 && !active}
                    onHover={(h) => {
                      if (h) {
                        cancelClear();
                        setExpandedId(node.id);
                      }
                    }}
                    onOpen={() => navigate(`/director/${node.id}`)}
                  />
                  {active && node.ring2.length > 0 && (
                    <Ring2Cluster
                      anchor={pos}
                      nodes={node.ring2}
                      theme={theme}
                      colors={colors}
                      onOpen={(id) => navigate(`/director/${id}`)}
                    />
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      )}
    </div>
  );
}

function Ring2Cluster({
  anchor,
  nodes,
  theme,
  colors,
  onOpen,
}: {
  anchor: { x: number; y: number; angle: number };
  nodes: RadialPerson[];
  theme: 'on-dark' | 'on-light';
  colors: { ray: string; rayActive: string };
  onOpen: (id: number) => void;
}) {
  const away = Math.atan2(anchor.y, anchor.x);
  const span = Math.PI;
  const start = away - span / 2;
  const ring2Count = RING2_SLOTS;
  const slots = Array.from({ length: ring2Count }, (_, i) => {
    const angle =
      ring2Count <= 1 ? away : start + (i / (ring2Count - 1)) * span;
    return {
      angle,
      x: anchor.x + Math.cos(angle) * RING2_RADIUS,
      y: anchor.y + Math.sin(angle) * RING2_RADIUS,
    };
  });

  return (
    <g>
      {slots.map((slot, idx) => {
        const node = nodes[idx];
        const endR = node ? RING2_SIZE / 2 : PLACEHOLDER_SIZE / 3;
        return (
          <line
            key={`r2-ray-${idx}`}
            x1={anchor.x + Math.cos(slot.angle) * (RING1_SIZE / 2)}
            y1={anchor.y + Math.sin(slot.angle) * (RING1_SIZE / 2)}
            x2={slot.x - Math.cos(slot.angle) * endR}
            y2={slot.y - Math.sin(slot.angle) * endR}
            stroke={colors.rayActive}
            strokeWidth={1}
          />
        );
      })}
      {slots.map((slot, idx) => {
        const node = nodes[idx];
        if (!node) return null;
        return (
          <GraphNode
            key={node.id}
            cx={slot.x}
            cy={slot.y}
            size={RING2_SIZE}
            name={node.name}
            image={node.image}
            theme={theme}
            small
            onOpen={() => onOpen(node.id)}
          />
        );
      })}
    </g>
  );
}

function GraphNode({
  cx,
  cy,
  size,
  name,
  image,
  isCenter,
  theme,
  dimmed,
  small,
  onHover,
  onOpen,
}: {
  cx: number;
  cy: number;
  size: number;
  name: string;
  image?: string | null;
  isCenter?: boolean;
  theme: 'on-dark' | 'on-light';
  dimmed?: boolean;
  small?: boolean;
  onHover?: (hovering: boolean) => void;
  onOpen: () => void;
}) {
  const r = size / 2;
  const clipId = `pg-${cx}-${cy}-${size}`;
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
  const labelGap = small ? 10 : isCenter ? 16 : 12;
  const labelY = r + labelGap;
  const labelFill = theme === 'on-light' ? '#42473F' : '#FFFFFF';
  const labelStroke = theme === 'on-light' ? 'rgba(255,255,255,0.85)' : 'rgba(26,24,21,0.75)';
  const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  return (
    <g
      style={{
        transform: `translate(${cx}px, ${cy}px)`,
        opacity: dimmed ? 0.38 : 1,
        cursor: 'pointer',
        transition: 'opacity 0.35s ease',
      }}
      onMouseEnter={() => onHover?.(true)}
      onMouseLeave={() => onHover?.(false)}
      onClick={(e) => {
        e.stopPropagation();
        if (clickTimer.current) clearTimeout(clickTimer.current);
        clickTimer.current = setTimeout(() => {
          clickTimer.current = null;
          onHover?.(true);
        }, 260);
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        if (clickTimer.current) clearTimeout(clickTimer.current);
        onOpen();
      }}
    >
      <defs>
        <clipPath id={clipId}>
          <circle cx={0} cy={0} r={r} />
        </clipPath>
      </defs>
      <circle cx={0} cy={0} r={r} fill={isCenter ? '#48473F' : '#34332D'} />
      {image ? (
        <image
          x={-r}
          y={-r}
          width={size}
          height={size}
          href={image}
          preserveAspectRatio="xMidYMid slice"
          clipPath={`url(#${clipId})`}
        />
      ) : (
        <text
          x={0}
          y={0}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#FAF6EE"
          style={{ fontSize: r * 0.5, fontWeight: 600 }}
        >
          {initials}
        </text>
      )}
      <circle
        cx={0}
        cy={0}
        r={r}
        fill="none"
        stroke={isCenter ? '#F6D77E' : theme === 'on-light' ? 'rgba(66,47,51,0.35)' : 'rgba(255,255,255,0.4)'}
        strokeWidth={isCenter ? 2.5 : 1.5}
      />
      <text
        x={0}
        y={labelY}
        textAnchor="middle"
        dominantBaseline="hanging"
        fill={labelFill}
        stroke={labelStroke}
        strokeWidth={2}
        paintOrder="stroke fill"
        style={{
          fontSize: Math.round((small ? 11 : isCenter ? 16 : 13) * SITE_UI_SCALE),
          fontWeight: 500,
          pointerEvents: 'none',
        }}
      >
        {name.length > 22 ? `${name.slice(0, 21)}…` : name}
      </text>
    </g>
  );
}
