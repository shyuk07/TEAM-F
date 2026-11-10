import { vi } from 'vitest';
import type { LocationProvider, LocationResult } from '@/features/offers';

/**
 * result가 있으면 곧바로 그 결과로 풀리고, null이면 resolve()를 부를 때까지 대기한다(수동).
 * 포트 계약대로 거절하지 않는다.
 */
export class FakeLocationProvider implements LocationProvider {
  private waiting: Array<(r: LocationResult) => void> = [];

  constructor(public result: LocationResult | null = null) {}

  current = vi.fn<LocationProvider['current']>((signal) => {
    void signal;
    if (this.result !== null) return Promise.resolve(this.result);
    return new Promise<LocationResult>((res) => {
      this.waiting.push(res);
    });
  });

  /** 대기 중인 모든 요청을 이 결과로 푼다. */
  resolve(r: LocationResult) {
    const pending = this.waiting;
    this.waiting = [];
    for (const res of pending) res(r);
  }
}

export const located: LocationResult = { status: 'located', point: { lat: 37.5, lng: 126.9 } };
export const unavailable: LocationResult = { status: 'unavailable' };
