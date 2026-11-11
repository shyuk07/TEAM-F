import type { GeoPoint, RadiusKm } from './nearbyQuery';

// TODO: 설계안 문서 생략(발표 시연 일정). docs/design/frontend에 위치 지도 결정을 기록한다.
// TODO: 임시 기본 중심(망원동). 기기 위치가 없을 때의 정본 중심이 정해지면 바꾼다.
export const DEFAULT_MAP_CENTER: GeoPoint = { lat: 37.5563, lng: 126.902 };

const KM_PER_DEGREE = 111;
const fixed = (n: number) => n.toFixed(5);

// OpenStreetMap 임베드 URL. 범위는 중심에서 반경만큼 위아래·좌우 여백(소수 5자리).
export function mapEmbedUrl(center: GeoPoint, radiusKm: RadiusKm): string {
  const dLat = radiusKm / KM_PER_DEGREE;
  const dLng = radiusKm / (KM_PER_DEGREE * Math.cos((center.lat * Math.PI) / 180));
  const bbox = [center.lng - dLng, center.lat - dLat, center.lng + dLng, center.lat + dLat]
    .map(fixed)
    .join(',');
  const marker = `${fixed(center.lat)},${fixed(center.lng)}`;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${marker}`;
}
