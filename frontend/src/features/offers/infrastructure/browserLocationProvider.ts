import type { LocationProvider, LocationResult } from '../application/ports';

// open-issues: C1a 위치는 현재 위치만 사용한다(주소 → 좌표 변환 확인 필요).
export class BrowserLocationProvider implements LocationProvider {
  current(signal?: AbortSignal): Promise<LocationResult> {
    return new Promise<LocationResult>((resolve) => {
      const unavailable: LocationResult = { status: 'unavailable' };
      const geo = typeof navigator === 'undefined' ? undefined : navigator.geolocation;
      if (signal?.aborted || !geo) {
        resolve(unavailable);
        return;
      }
      try {
        geo.getCurrentPosition(
          (pos) => {
            // 위치 값은 저장하지 않는다(D-29). 정리된 요청이면 결과를 쓰지 않는다.
            resolve(
              signal?.aborted
                ? unavailable
                : {
                    status: 'located',
                    point: { lat: pos.coords.latitude, lng: pos.coords.longitude },
                  },
            );
          },
          () => resolve(unavailable),
          { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
        );
      } catch {
        resolve(unavailable);
      }
    });
  }
}
