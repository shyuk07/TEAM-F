import { KAKAO_MAP_JS_KEY } from '@/shared/config/env';
import type { MapRenderer } from '../application/ports';
import type { GeoPoint } from '../domain/nearbyQuery';

// 이 구현체가 쓰는 카카오맵 SDK 표면만 최소로 선언한다.
type KakaoLatLng = object;
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
  ) => object;
  Marker: new (opts: { map: object; position: KakaoLatLng }) => object;
}
declare global {
  interface Window {
    kakao?: { maps: KakaoMaps };
  }
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
    opts: { center: GeoPoint; level: number },
    signal?: AbortSignal,
  ): Promise<void> {
    if (!this.appKey) throw new Error('kakao map key missing');
    const maps = await loadSdk(this.appKey);
    if (signal?.aborted) return;
    const position = new maps.LatLng(opts.center.lat, opts.center.lng);
    const map = new maps.Map(el, {
      center: position,
      level: opts.level,
      draggable: false,
      scrollwheel: false,
      disableDoubleClickZoom: true,
    });
    new maps.Marker({ map, position });
  }
}
