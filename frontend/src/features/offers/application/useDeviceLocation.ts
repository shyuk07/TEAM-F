import { useCallback, useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { GeoPoint } from '../domain/nearbyQuery';
import { LocationProviderToken } from './tokens';

export type DeviceLocation = {
  status: 'pending' | 'ok' | 'unavailable';
  point: GeoPoint | null;
  request(): void;
};

type LocationState = Pick<DeviceLocation, 'status' | 'point'>;

// 마운트 때 한 번 기기 위치를 묻는다. 거부·실패·초과는 모두 unavailable(customer-home.md D-9).
export function useDeviceLocation(): DeviceLocation {
  const provider = useDep(LocationProviderToken);
  const [state, setState] = useState<LocationState>({ status: 'pending', point: null });
  // request()가 바꾸면 effect가 다시 묻는다.
  const [attempt, setAttempt] = useState(0);
  const pendingRef = useRef(true);

  useEffect(() => {
    const ctrl = new AbortController();
    pendingRef.current = true;
    const settle = (point: GeoPoint | null) => {
      // 언마운트·재요청으로 정리된 뒤에는 상태를 바꾸지 않는다(F10).
      if (ctrl.signal.aborted) return;
      pendingRef.current = false;
      setState(point !== null ? { status: 'ok', point } : { status: 'unavailable', point: null });
    };
    provider.current(ctrl.signal).then(settle, () => settle(null));
    return () => ctrl.abort();
  }, [provider, attempt]);

  const request = useCallback(() => {
    if (pendingRef.current) return;
    pendingRef.current = true;
    setState({ status: 'pending', point: null });
    setAttempt((n) => n + 1);
  }, []);

  return { status: state.status, point: state.point, request };
}
