import type { GeoPoint } from '../domain/nearbyQuery';

// 유스케이스 전용 기술 기능(기기 위치). 실패·거부·초과는 throw하지 않고 null(customer-home.md D-9).
export interface LocationProvider {
  current(signal?: AbortSignal): Promise<GeoPoint | null>;
}
