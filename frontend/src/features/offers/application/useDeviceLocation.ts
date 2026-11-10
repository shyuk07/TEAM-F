import type { GeoPoint } from '../domain/nearbyQuery';

export type DeviceLocation = {
  status: 'pending' | 'ok' | 'unavailable';
  point: GeoPoint | null;
  request(): void;
};

export function useDeviceLocation(): DeviceLocation {
  throw new Error('not implemented: useDeviceLocation');
}
