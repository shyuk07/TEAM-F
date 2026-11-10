import { useEffect, useState } from 'react';

const DEFAULT_INTERVAL_MS = 30_000;

// 현재 시각을 intervalMs(기본 30초)마다 갱신한다(customer-home.md D-14).
export function useNow(intervalMs: number = DEFAULT_INTERVAL_MS): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
