import type { LocationProvider } from '../application/ports';
import type { GeoPoint } from '../domain/nearbyQuery';

export class BrowserLocationProvider implements LocationProvider {
  current(signal?: AbortSignal): Promise<GeoPoint | null> {
    void signal;
    throw new Error('not implemented: BrowserLocationProvider.current');
  }
}
