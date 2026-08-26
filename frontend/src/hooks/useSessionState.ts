import { useCallback, useState, type Dispatch, type SetStateAction } from "react";

const memoryState = new Map<string, unknown>();

export function useSessionState<T>(key: string, initialValue: T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    if (memoryState.has(key)) return memoryState.get(key) as T;
    try {
      const saved = sessionStorage.getItem(key);
      const restored = saved === null ? initialValue : JSON.parse(saved) as T;
      memoryState.set(key, restored);
      return restored;
    } catch {
      return initialValue;
    }
  });

  const update = useCallback<Dispatch<SetStateAction<T>>>((action) => {
    setValue((current) => {
      const next = typeof action === "function" ? (action as (value: T) => T)(current) : action;
      memoryState.set(key, next);
      try {
        if (next === undefined) sessionStorage.removeItem(key);
        else sessionStorage.setItem(key, JSON.stringify(next));
      } catch {
        // Large channel results still remain available in memory while the app is open.
      }
      return next;
    });
  }, [key]);

  return [value, update];
}

