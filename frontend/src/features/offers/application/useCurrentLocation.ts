import { useCallback, useEffect, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { GeoPoint, LocationStatus } from '../domain/search';
import { LocationProviderToken } from './tokens';

type LocationState = { status: LocationStatus; point: GeoPoint | null };

const LOCATING: LocationState = { status: 'locating', point: null };
const UNAVAILABLE: LocationState = { status: 'unavailable', point: null };

export function useCurrentLocation(): {
  status: LocationStatus;
  point: GeoPoint | null;
  retry(): void;
} {
  const provider = useDep(LocationProviderToken);
  const [state, setState] = useState<LocationState>(LOCATING);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    provider.current(ctrl.signal).then(
      (result) => {
        if (ctrl.signal.aborted) return;
        setState(
          result.status === 'located' ? { status: 'located', point: result.point } : UNAVAILABLE,
        );
      },
      () => {
        if (!ctrl.signal.aborted) setState(UNAVAILABLE);
      },
    );
    return () => ctrl.abort();
  }, [provider, nonce]);

  const retry = useCallback(() => {
    setState(LOCATING);
    setNonce((n) => n + 1);
  }, []);

  return { status: state.status, point: state.point, retry };
}
