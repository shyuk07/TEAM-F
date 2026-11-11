import type { GeoPoint } from '../domain/nearbyQuery';

// 유스케이스 전용 기술 기능(기기 위치). 실패·거부·초과는 throw하지 않고 null(customer-home.md D-9).
export interface LocationProvider {
  current(signal?: AbortSignal): Promise<GeoPoint | null>;
}

// 유스케이스 전용 기술 기능(지도 그리기). 키가 없거나 로드·렌더에 실패하면 reject한다(호출부가 폴백).
export interface MapRenderer {
  render(
    el: HTMLElement,
    opts: { center: GeoPoint; level: number; radiusM: number; interactive?: boolean },
    signal?: AbortSignal,
  ): Promise<void>;
}
