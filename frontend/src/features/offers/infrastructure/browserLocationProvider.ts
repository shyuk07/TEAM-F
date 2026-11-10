import type { LocationProvider } from '../application/ports';
import type { GeoPoint } from '../domain/nearbyQuery';

// 8초 안에 답이 없으면 위치 없음, 5분 안의 위치는 다시 쓴다(customer-home.md D-9).
const POSITION_OPTIONS: PositionOptions = {
  enableHighAccuracy: false,
  timeout: 8000,
  maximumAge: 300000,
};

export class BrowserLocationProvider implements LocationProvider {
  current(signal?: AbortSignal): Promise<GeoPoint | null> {
    const geolocation = typeof navigator !== 'undefined' ? navigator.geolocation : undefined;
    if (geolocation === undefined || geolocation === null || signal?.aborted) {
      return Promise.resolve(null);
    }
    // 거부·실패·시간 초과·abort는 throw하지 않고 null이다.
    return new Promise((resolve) => {
      let settled = false;
      const finish = (point: GeoPoint | null) => {
        if (settled) return;
        settled = true;
        signal?.removeEventListener('abort', onAbort);
        resolve(point);
      };
      const onAbort = () => finish(null);
      signal?.addEventListener('abort', onAbort);
      geolocation.getCurrentPosition(
        (pos) => finish({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => finish(null),
        POSITION_OPTIONS,
      );
    });
  }
}
