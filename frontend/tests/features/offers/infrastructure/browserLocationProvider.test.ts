import { BrowserLocationProvider } from '@/features/offers/infrastructure/browserLocationProvider';

type Success = (pos: { coords: { latitude: number; longitude: number } }) => void;
type Failure = (err: { code: number; message: string }) => void;

const original = Object.getOwnPropertyDescriptor(navigator, 'geolocation');

function setGeolocation(value: unknown) {
  Object.defineProperty(navigator, 'geolocation', { value, configurable: true });
}

describe('BrowserLocationProvider.current', () => {
  afterEach(() => {
    if (original) Object.defineProperty(navigator, 'geolocation', original);
    else Reflect.deleteProperty(navigator, 'geolocation');
  });

  it('성공하면 {lat, lng}이고 옵션은 timeout 8000·maximumAge 300000·enableHighAccuracy false', async () => {
    const getCurrentPosition = vi.fn((...args: [Success, Failure, PositionOptions]) => {
      args[0]({ coords: { latitude: 37.556, longitude: 126.901 } });
    });
    setGeolocation({ getCurrentPosition });
    await expect(new BrowserLocationProvider().current()).resolves.toEqual({
      lat: 37.556,
      lng: 126.901,
    });
    expect(getCurrentPosition.mock.calls[0]?.[2]).toEqual({
      enableHighAccuracy: false,
      timeout: 8000,
      maximumAge: 300000,
    });
  });

  it('오류 콜백(거부·시간 초과)이면 null(throw 안 함)', async () => {
    const getCurrentPosition = vi.fn((...args: [Success, Failure]) => {
      args[1]({ code: 1, message: 'denied' });
    });
    setGeolocation({ getCurrentPosition });
    await expect(new BrowserLocationProvider().current()).resolves.toBeNull();
  });

  it('navigator.geolocation이 없으면 null', async () => {
    setGeolocation(undefined);
    await expect(new BrowserLocationProvider().current()).resolves.toBeNull();
  });
});
