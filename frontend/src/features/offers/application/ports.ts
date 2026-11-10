import type { GeoPoint } from '../domain/search';

export type LocationResult = { status: 'located'; point: GeoPoint } | { status: 'unavailable' };

export interface LocationProvider {
  current(signal?: AbortSignal): Promise<LocationResult>;
}
