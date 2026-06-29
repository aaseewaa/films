import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export interface GraphHeaderState {
  centerLine: ReactNode;
  statsLine: ReactNode;
  loading: boolean;
  onRandomDirector: (() => void) | null;
  randomDisabled: boolean;
}

const EMPTY_STATE: GraphHeaderState = {
  centerLine: null,
  statsLine: null,
  loading: false,
  onRandomDirector: null,
  randomDisabled: true,
};

type GraphHeaderContextValue = {
  state: GraphHeaderState;
  setGraphHeader: (next: Partial<GraphHeaderState>) => void;
  clearGraphHeader: () => void;
};

const GraphHeaderContext = createContext<GraphHeaderContextValue | null>(null);

export function GraphHeaderProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GraphHeaderState>(EMPTY_STATE);

  const setGraphHeader = useCallback((next: Partial<GraphHeaderState>) => {
    setState((prev) => ({ ...prev, ...next }));
  }, []);

  const clearGraphHeader = useCallback(() => {
    setState(EMPTY_STATE);
  }, []);

  const value = useMemo(
    () => ({ state, setGraphHeader, clearGraphHeader }),
    [state, setGraphHeader, clearGraphHeader],
  );

  return (
    <GraphHeaderContext.Provider value={value}>{children}</GraphHeaderContext.Provider>
  );
}

export function useGraphHeader() {
  const ctx = useContext(GraphHeaderContext);
  if (!ctx) {
    throw new Error('useGraphHeader must be used within GraphHeaderProvider');
  }
  return ctx;
}
