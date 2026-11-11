import { mapEmbedUrl } from '../domain/locationMap';
import type { GeoPoint, RadiusKm } from '../domain/nearbyQuery';

// TODO: iframe title 「지도」는 임시 문구다. 정본 문구가 정해지면 바꾼다.
const MAP_TITLE = '지도';

// C1a 시트 위 .dim 자리의 보기 전용 지도. 감싸는 요소 없이 iframe 하나만 두고 pointer-events: none으로
// 클릭이 .dim에 그대로 닿게 해 빈 곳 클릭 닫기(Overlay의 e.target === dim 판정)를 유지한다.
export function LocationMap({ center, radiusKm }: { center: GeoPoint; radiusKm: RadiusKm }) {
  return (
    <iframe
      title={MAP_TITLE}
      src={mapEmbedUrl(center, radiusKm)}
      tabIndex={-1}
      style={{ pointerEvents: 'none', flex: 1, border: 0, width: '100%' }}
    />
  );
}
