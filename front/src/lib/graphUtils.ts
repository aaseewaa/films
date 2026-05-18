/**
 * Утилиты для подготовки данных графа к визуализации.
 *
 * Главная задача: если у режиссёра в БД мало связей, дорисовываем
 * "серые placeholders" чтобы граф визуально был полным.
 */
import type { GraphResponse, GraphNode, GraphLink } from '@/api/types';

export interface EnrichedNode extends GraphNode {
  depth: number;          // расстояние от центра (0, 1, 2, 3, 4)
  isPlaceholder: boolean; // true для серых заглушек
  __photoLoaded?: boolean;
  __photoImg?: HTMLImageElement;
}

export interface EnrichedGraph {
  nodes: EnrichedNode[];
  links: GraphLink[];
  centerId: number;
}

/**
 * Вычисляет глубину каждого узла от центра через BFS.
 * Узлы за пределами maxDepth отбрасываются.
 */
function computeDepths(
  raw: GraphResponse,
  centerId: number,
  maxDepth: number
): Map<number, number> {
  const depths = new Map<number, number>();
  depths.set(centerId, 0);

  // Adjacency list
  const adj = new Map<number, Set<number>>();
  raw.links.forEach((link) => {
    const s = typeof link.source === 'object' ? (link.source as any).id : link.source;
    const t = typeof link.target === 'object' ? (link.target as any).id : link.target;
    if (!adj.has(s)) adj.set(s, new Set());
    if (!adj.has(t)) adj.set(t, new Set());
    adj.get(s)!.add(t);
    adj.get(t)!.add(s);
  });

  // BFS
  const queue: number[] = [centerId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentDepth = depths.get(current)!;
    if (currentDepth >= maxDepth) continue;

    const neighbors = adj.get(current) || new Set();
    neighbors.forEach((n) => {
      if (!depths.has(n)) {
        depths.set(n, currentDepth + 1);
        queue.push(n);
      }
    });
  }

  return depths;
}

/**
 * Главная функция: подготовить граф для рендеринга.
 *  - вычисляет глубины через BFS от центра
 *  - выбрасывает узлы дальше maxDepth
 *  - дорисовывает placeholders вокруг разреженных режиссёров
 */
export function enrichGraph(
  raw: GraphResponse,
  centerId: number,
  options: {
    maxDepth?: number;
    minConnectionsPerNode?: number;
    placeholdersPerSparseNode?: number;
  } = {}
): EnrichedGraph {
  const maxDepth = options.maxDepth ?? 3;
  const minConn = options.minConnectionsPerNode ?? 3;
  const placeholdersToAdd = options.placeholdersPerSparseNode ?? 3;

  // 1. Вычисляем глубины
  const depths = computeDepths(raw, centerId, maxDepth);

  // 2. Фильтруем узлы по глубине
  const visibleIds = new Set(depths.keys());
  const baseNodes: EnrichedNode[] = raw.nodes
    .filter((n) => visibleIds.has(n.id))
    .map((n) => ({
      ...n,
      depth: depths.get(n.id) ?? maxDepth,
      isPlaceholder: false,
    }));

  // 3. Фильтруем связи: оба конца должны быть видны
  const baseLinks: GraphLink[] = raw.links.filter((link) => {
    const s = typeof link.source === 'object' ? (link.source as any).id : link.source;
    const t = typeof link.target === 'object' ? (link.target as any).id : link.target;
    return visibleIds.has(s) && visibleIds.has(t);
  });

  // 4. Считаем степень каждого видимого узла
  const degree = new Map<number, number>();
  baseLinks.forEach((link) => {
    const s = typeof link.source === 'object' ? (link.source as any).id : link.source;
    const t = typeof link.target === 'object' ? (link.target as any).id : link.target;
    degree.set(s, (degree.get(s) ?? 0) + 1);
    degree.set(t, (degree.get(t) ?? 0) + 1);
  });

  // 5. Дорисовываем placeholders для разреженных узлов
  const allNodes: EnrichedNode[] = [...baseNodes];
  const allLinks: GraphLink[] = [...baseLinks];
  let phCounter = -1; // отрицательные id для placeholders

  baseNodes.forEach((node) => {
    if (node.depth >= maxDepth) return; // нет смысла дорисовывать на самом краю
    const currentDeg = degree.get(node.id) ?? 0;
    if (currentDeg >= minConn) return;

    const need = placeholdersToAdd;
    for (let i = 0; i < need; i++) {
      const phId = phCounter--;
      allNodes.push({
        id: phId,
        name: '',
        image: null,
        depth: node.depth + 1,
        isPlaceholder: true,
      });
      allLinks.push({
        source: node.id,
        target: phId,
        weight: 0,
      });
    }
  });

  return {
    nodes: allNodes,
    links: allLinks,
    centerId,
  };
}

/**
 * Радиус узла по глубине от центра.
 * Центр огромный, дальше меньше — но даже на 4 уровне читаемо.
 */
export function nodeRadiusByDepth(depth: number): number {
  switch (depth) {
    case 0: return 60;  // центр (~120px диаметр на экране)
    case 1: return 32;  // первая глубина (~64px)
    case 2: return 22;  // вторая
    case 3: return 16;  // третья
    case 4: return 12;  // четвёртая (если будет)
    default: return 10;
  }
}

/**
 * Цвет placeholder-узла.
 * Серый, лёгкий, ненавязчивый — это "пустые места" в графе.
 */
export const PLACEHOLDER_COLOR = 'rgba(232, 223, 200, 0.18)';
