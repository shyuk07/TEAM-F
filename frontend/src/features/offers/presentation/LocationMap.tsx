import { useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { MapRendererToken } from '../application/tokens';
import { kakaoMapLevel, mapEmbedUrl } from '../domain/locationMap';
import type { GeoPoint, RadiusKm } from '../domain/nearbyQuery';

// TODO: 「지도」는 임시 문구다. 정본 문구가 정해지면 바꾼다.
const MAP_LABEL = '지도';
const MAP_STYLE = { flex: 1, border: 0, width: '100%' } as const;

// C1a 시트 위 .dim 자리의 지도(드래그·확대 가능). 감싸는 요소 없는 div 하나에 MapRenderer(카카오맵)로 그리고,
// 렌더 실패(키 없음·로드 실패) 시 OSM iframe(mapEmbedUrl)로 폴백한다. center·radius가 바뀌면 다시 그리고
// 언마운트 시 abort한다. 지도를 누르면 target이 지도라 Overlay의 e.target === dim 판정에 걸리지 않아 시트가 유지되고,
// 지도 밖 빈 .dim을 누르면 닫힌다.
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
      .render(
        el,
        {
          center: { lat, lng },
          level: kakaoMapLevel(radiusKm),
          radiusM: radiusKm * 1000,
          interactive: true,
        },
        controller.signal,
      )
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
        style={MAP_STYLE}
      />
    );
  }
  return <div ref={ref} role="img" aria-label={MAP_LABEL} style={MAP_STYLE} />;
}
