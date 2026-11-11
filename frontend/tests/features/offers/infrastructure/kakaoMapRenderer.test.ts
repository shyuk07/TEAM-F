import { KakaoMapRenderer } from '@/features/offers/infrastructure/kakaoMapRenderer';

describe('KakaoMapRenderer', () => {
  it('키가 빈 문자열이면 스크립트를 넣지 않고 reject한다(동기 throw 아님)', async () => {
    const before = document.querySelectorAll('script').length;
    const renderer = new KakaoMapRenderer('');
    const el = document.createElement('div');
    let result: Promise<void> | undefined;
    expect(() => {
      result = renderer.render(el, {
        center: { lat: 37.5563, lng: 126.902 },
        level: 6,
        radiusM: 3000,
      });
    }).not.toThrow();
    await expect(result).rejects.toBeInstanceOf(Error);
    expect(document.querySelectorAll('script')).toHaveLength(before);
  });
});
