import type { LocationStatus } from './search';

export const MIN_RADIUS_KM = 0.1;
export const MAX_RADIUS_KM = 20;
export const RADIUS_CHIPS: readonly number[] = [1, 3, 5, 10];

export function isValidRadiusKm(km: number): boolean {
  return Number.isFinite(km) && km >= MIN_RADIUS_KM && km <= MAX_RADIUS_KM;
}

export function formatRadiusKm(km: number): string {
  return `${km}km`;
}

// TODO: 시트 상태 줄이 「지금: 현재 위치」로 임시다. 와이어프레임은 「지금: 망원동 (현재 위치)」.
//   왜: 좌표 → 동 이름을 얻을 API가 없다 (docs/design/frontend/offers.md C-4, C-17, D-40, Q-13)
//   언제: 결정 후 (백엔드: 좌표 → 동 이름 변환 제공)
export function locationStatusLine(status: LocationStatus): string {
  if (status === 'located') return '지금: 현재 위치';
  return status === 'locating' ? '지금: 위치 확인 중' : '지금: 위치 없음';
}

export function canRefreshLocation(status: LocationStatus): boolean {
  return status !== 'locating';
}
