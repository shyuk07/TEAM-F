import { DEFAULT_MAP_CENTER, kakaoMapLevel, mapEmbedUrl } from '@/features/offers';

const BASE = 'https://www.openstreetmap.org/export/embed.html';
const center = { lat: 37.5563, lng: 126.902 };
const bboxOf = (url: string) => new URL(url).searchParams.get('bbox')!.split(',').map(Number);

describe('locationMap', () => {
  it('DEFAULT_MAP_CENTER는 망원동 {37.5563, 126.902}', () => {
    expect(DEFAULT_MAP_CENTER).toEqual({ lat: 37.5563, lng: 126.902 });
  });

  it('3km: bbox minLng,minLat,maxLng,maxLat(소수 5자리), layer mapnik, marker lat,lng', () => {
    expect(mapEmbedUrl(center, 3)).toBe(
      `${BASE}?bbox=126.86791,37.52927,126.93609,37.58333&layer=mapnik&marker=37.55630,126.90200`,
    );
  });

  it('1km 경계', () => {
    expect(mapEmbedUrl(center, 1)).toBe(
      `${BASE}?bbox=126.89064,37.54729,126.91336,37.56531&layer=mapnik&marker=37.55630,126.90200`,
    );
  });

  it('10km 경계', () => {
    expect(mapEmbedUrl(center, 10)).toBe(
      `${BASE}?bbox=126.78836,37.46621,127.01564,37.64639&layer=mapnik&marker=37.55630,126.90200`,
    );
  });

  it('반경이 클수록 bbox가 넓어진다', () => {
    const [a, b, c, d] = bboxOf(mapEmbedUrl(center, 1));
    const [e, f, g, h] = bboxOf(mapEmbedUrl(center, 10));
    expect(g! - e!).toBeGreaterThan(c! - a!);
    expect(h! - f!).toBeGreaterThan(d! - b!);
  });

  it.each([
    [1, 6],
    [3, 8],
    [5, 8],
    [10, 9],
  ] as const)('kakaoMapLevel(%i) = %i', (r, level) => {
    expect(kakaoMapLevel(r)).toBe(level);
  });
});
