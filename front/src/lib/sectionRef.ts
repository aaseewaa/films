import { useRef, type RefObject } from 'react';

/** Ref для `<section>` (HTMLElement — без HTMLSectionElement в DOM-типах TS). */
export function useSectionRef(): RefObject<HTMLElement> {
  return useRef(null) as RefObject<HTMLElement>;
}

/** Ref для `<div>`. */
export function useDivRef(): RefObject<HTMLDivElement> {
  return useRef(null) as RefObject<HTMLDivElement>;
}
