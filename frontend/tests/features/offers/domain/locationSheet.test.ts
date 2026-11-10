import {
  MAX_RADIUS_KM,
  MIN_RADIUS_KM,
  RADIUS_CHIPS,
  canRefreshLocation,
  formatRadiusKm,
  isValidRadiusKm,
  locationStatusLine,
} from '@/features/offers/domain/locationSheet';
import { DEFAULT_RADIUS_KM, WIDEN_RADIUS_KM } from '@/features/offers/domain/search';

describe('isValidRadiusKm', () => {
  it.each([
    [0.1, true],
    [0.09, false],
    [0, false],
    [-1, false],
    [3, true],
    [20, true],
    [20.1, false],
    [Number.NaN, false],
    [Number.POSITIVE_INFINITY, false],
  ])('%s → %s', (km, expected) => {
    expect(isValidRadiusKm(km)).toBe(expected);
  });
});

describe('RADIUS_CHIPS', () => {
  it('[1, 3, 5, 10]이고 모두 유효하며 기본·넓히기 반경을 포함한다', () => {
    expect(RADIUS_CHIPS).toEqual([1, 3, 5, 10]);
    for (const km of RADIUS_CHIPS) expect(isValidRadiusKm(km)).toBe(true);
    expect(RADIUS_CHIPS).toContain(DEFAULT_RADIUS_KM);
    expect(RADIUS_CHIPS).toContain(WIDEN_RADIUS_KM);
    expect(MIN_RADIUS_KM).toBe(0.1);
    expect(MAX_RADIUS_KM).toBe(20);
  });
});

describe('formatRadiusKm', () => {
  it.each([
    [1, '1km'],
    [3, '3km'],
    [10, '10km'],
    [0.5, '0.5km'],
  ])('%s → %s', (km, expected) => {
    expect(formatRadiusKm(km)).toBe(expected);
  });
});

describe('locationStatusLine', () => {
  it.each([
    ['located', '지금: 현재 위치'],
    ['locating', '지금: 위치 확인 중'],
    ['unavailable', '지금: 위치 없음'],
  ] as const)('%s → %s', (status, expected) => {
    expect(locationStatusLine(status)).toBe(expected);
  });
});

describe('canRefreshLocation', () => {
  it.each([
    ['locating', false],
    ['located', true],
    ['unavailable', true],
  ] as const)('%s → %s', (status, expected) => {
    expect(canRefreshLocation(status)).toBe(expected);
  });
});
