import { useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { MapRendererToken } from '../application/tokens';
import { kakaoMapLevel, mapEmbedUrl } from '../domain/locationMap';
import type { GeoPoint, RadiusKm } from '../domain/nearbyQuery';

// TODO: 「지도」는 임시 문구다. 정본 문구가 정해지면 바꾼다.
const MAP_LABEL = '지도';
const VIEW_ONLY_STYLE = { pointerEvents: 'none', flex: 1, border: 0, width: '100%' } as const;

// C1a 시트 위 .dim 자리의 보기 전용 지도. 감싸는 요소 없는 div 하나에 MapRenderer(카카오맵)로 그리고,
// 렌더 실패(키 없음·로드 실패) 시 OSM iframe(mapEmbedUrl)로 폴백한다. center·radius가 바뀌면 다시 그리고
// 언마운트 시 abort한다. pointer-events none이라 클릭이 .dim에 닿아 빈 곳 클릭 닫기가 유지된다.
export function LocationMap({ center, radiusKm }: { center: GeoPoint; radiusKm: RadiusKm }) {
  const renderer = useDep(MapRendererToken);
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const { lat, lng } = center;

  useEffect(() => {
    const el = ref.current;
    if (!el || failed) return;
    const controller = new AbortController();
    renderer
      .render(el, { center: { lat, lng }, level: kakaoMapLevel(radiusKm) }, controller.signal)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [renderer, lat, lng, radiusKm, failed]);

  if (failed) {
    return (
      <iframe
        title={MAP_LABEL}
        src={mapEmbedUrl(center, radiusKm)}
        tabIndex={-1}
        style={VIEW_ONLY_STYLE}
      />
    );
  }
  return <div ref={ref} role="img" aria-label={MAP_LABEL} style={VIEW_ONLY_STYLE} />;
}
