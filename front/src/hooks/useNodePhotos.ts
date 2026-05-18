import { useEffect, useRef, useState } from 'react';
import type { EnrichedNode } from '@/lib/graphUtils';

/**
 * Предзагружает фото для всех узлов графа в HTMLImageElement.
 * Это нужно для canvas-рендеринга в react-force-graph — изображения
 * должны быть готовы к моменту drawImage(), иначе будут "мигать".
 *
 * Возвращает Map<nodeId, HTMLImageElement>.
 */
export function useNodePhotos(nodes: EnrichedNode[]): Map<number, HTMLImageElement> {
  const cacheRef = useRef<Map<number, HTMLImageElement>>(new Map());
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    nodes.forEach((node) => {
      if (node.isPlaceholder || !node.image) return;
      if (cacheRef.current.has(node.id)) return;

      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        cacheRef.current.set(node.id, img);
        forceUpdate((v) => v + 1);
      };
      img.onerror = () => {
        // Если не загрузилось — оставляем без фото, нарисуем серый круг
      };
      img.src = node.image;
    });
  }, [nodes]);

  return cacheRef.current;
}
