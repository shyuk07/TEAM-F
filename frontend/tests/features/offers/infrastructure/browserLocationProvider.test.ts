import { BrowserLocationProvider } from '@/features/offers/infrastructure/browserLocationProvider';

type Success = (pos: { coords: { latitude: number; longitude: number } }) => void;
type Failure = (err: { code: number; message: string }) => void;

function stubGeolocation(
  impl: (success: Success, failure: Failure, options?: PositionOptions) => void,
) {
  const getCurrentPosition = vi.fn(impl);
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: { getCurrentPosition },
  });
  return getCurrentPosition;
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'geolocation');
});

describe('BrowserLocationProvider.current', () => {
  const provider = new BrowserLocationProvider();

  it('성공하면 located와 좌표', async () => {
    stubGeolocation((ok) => ok({ coords: { latitude: 37.5, longitude: 126.9 } }));
    await expect(provider.current()).resolves.toEqual({
      status: 'located',
      point: { lat: 37.5, lng: 126.9 },
    });
  });

  it('오류 콜백(권한 거부)이면 unavailable', async () => {
    stubGeolocation((_ok, fail) => fail({ code: 1, message: 'denied' }));
    await expect(provider.current()).resolves.toEqual({ status: 'unavailable' });
  });

  it('geolocation이 없으면 unavailable', async () => {
    Reflect.deleteProperty(navigator, 'geolocation');
    await expect(provider.current()).resolves.toEqual({ status: 'unavailable' });
  });

  it('옵션으로 timeout 10000·maximumAge 300000을 넘긴다', async () => {
    const spy = stubGeolocation((ok) => ok({ coords: { latitude: 37.5, longitude: 126.9 } }));
    await provider.current();
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0][2]).toMatchObject({
      enableHighAccuracy: false,
      timeout: 10_000,
      maximumAge: 300_000,
    });
  });

  it('이미 abort된 signal이면 결과를 쓰지 않고, 거절하지는 않는다', async () => {
    stubGeolocation((ok) => ok({ coords: { latitude: 37.5, longitude: 126.9 } }));
    const ctrl = new AbortController();
    ctrl.abort();
    await expect(provider.current(ctrl.signal)).resolves.toEqual({ status: 'unavailable' });
  });
});
