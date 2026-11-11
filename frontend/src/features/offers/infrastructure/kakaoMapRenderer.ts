import { KAKAO_MAP_JS_KEY } from '@/shared/config/env';
import type { MapRenderer } from '../application/ports';
import type { GeoPoint } from '../domain/nearbyQuery';

// 이 구현체가 쓰는 카카오맵 SDK 표면만 최소로 선언한다.
type KakaoLatLng = object;
interface KakaoMap {
  setCenter(latlng: KakaoLatLng): void;
  setLevel(level: number): void;
}
interface KakaoOverlay {
  setMap(map: KakaoMap | null): void;
}
interface KakaoMaps {
  load(callback: () => void): void;
  LatLng: new (lat: number, lng: number) => KakaoLatLng;
  Map: new (
    el: HTMLElement,
    opts: {
      center: KakaoLatLng;
      level: number;
      draggable: boolean;
      scrollwheel: boolean;
      disableDoubleClickZoom: boolean;
    },
  ) => KakaoMap;
  Marker: new (opts: { map: KakaoMap; position: KakaoLatLng }) => KakaoOverlay;
  Circle: new (opts: {
    map: KakaoMap;
    center: KakaoLatLng;
    radius: number;
    strokeWeight: number;
    strokeColor: string;
    strokeOpacity: number;
    fillColor: string;
    fillOpacity: number;
  }) => KakaoOverlay;
}
declare global {
  interface Window {
    kakao?: { maps: KakaoMaps };
  }
}

// el 단위로 지도를 재사용하고, 다시 그릴 때 이전 마커·원을 지워 겹치지 않게 한다.
type Drawn = { map: KakaoMap; overlays: KakaoOverlay[] };
const drawnByElement = new WeakMap<HTMLElement, Drawn>();

// 반경 원 색은 디자인 토큰 --accent에서 읽는다(F12, 하드코딩 색 금지).
function accentColor(): string {
  return getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
}

const SDK_URL = 'https://dapi.kakao.com/v2/maps/sdk.js';

// SDK는 모듈 단위로 한 번만 로드한다. 실패하면 캐시를 비워 다음 호출에서 다시 시도한다.
let sdkPromise: Promise<KakaoMaps> | null = null;

function loadSdk(appKey: string): Promise<KakaoMaps> {
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise<KakaoMaps>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `${SDK_URL}?appkey=${encodeURIComponent(appKey)}&autoload=false`;
    script.async = true;
    script.onload = () => {
      const maps = window.kakao?.maps;
      if (!maps) {
        reject(new Error('kakao maps sdk unavailable'));
        return;
      }
      maps.load(() => resolve(maps));
    };
    script.onerror = () => reject(new Error('kakao maps sdk load failed'));
    document.head.appendChild(script);
  }).catch((error: unknown) => {
    sdkPromise = null;
    throw error;
  });
  return sdkPromise;
}

// 카카오맵 JavaScript SDK 구현체. 보기 전용 Map(드래그·휠·더블클릭 확대 끔)과 가운데 Marker를 그린다.
// 키가 비면 스크립트를 넣지 않고 reject한다(호출부가 OSM으로 폴백).
export class KakaoMapRenderer implements MapRenderer {
  constructor(private readonly appKey: string = KAKAO_MAP_JS_KEY) {}

  async render(
    el: HTMLElement,
    opts: { center: GeoPoint; level: number; radiusM: number; interactive?: boolean },
    signal?: AbortSignal,
  ): Promise<void> {
    if (!this.appKey) throw new Error('kakao map key missing');
    const maps = await loadSdk(this.appKey);
    if (signal?.aborted) return;
    const interactive = opts.interactive ?? false;
    const position = new maps.LatLng(opts.center.lat, opts.center.lng);
    let drawn = drawnByElement.get(el);
    if (drawn) {
      drawn.map.setCenter(position);
      drawn.map.setLevel(opts.level);
      drawn.overlays.forEach((o) => o.setMap(null));
    } else {
      const map = new maps.Map(el, {
        center: position,
        level: opts.level,
        // interactive면 드래그·휠·더블클릭 확대를 켜고, 아니면 보기 전용으로 모두 끈다.
        // 지도는 el 단위로 재사용하므로 이 옵션은 처음 만들 때만 반영된다.
        draggable: interactive,
        scrollwheel: interactive,
        disableDoubleClickZoom: !interactive,
      });
      drawn = { map, overlays: [] };
      drawnByElement.set(el, drawn);
    }
    const color = accentColor();
    drawn.overlays = [
      new maps.Circle({
        map: drawn.map,
        center: position,
        radius: opts.radiusM,
        strokeWeight: 2,
        strokeColor: color,
        strokeOpacity: 0.8,
        fillColor: color,
        fillOpacity: 0.15,
      }),
      new maps.Marker({ map: drawn.map, position }),
    ];
  }
}
