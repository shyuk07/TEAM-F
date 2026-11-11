import { vi } from 'vitest';
import type { GeoPoint, LocationProvider } from '@/features/offers';

export const MANGWON: GeoPoint = { lat: 37.556, lng: 126.901 };

// 기본: 위치 없음(null)
export class FakeLocationProvider implements LocationProvider {
  current = vi.fn<LocationProvider['current']>(() => Promise.resolve(null));
}
