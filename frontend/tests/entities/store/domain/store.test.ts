import { describe, expect, it } from 'vitest';
import { storeStatusLabel, storeStatusTone } from '@/entities/store';

describe('entities/store domain storeStatusLabel', () => {
  it.each([
    ['ACTIVE' as const, '영업 중'],
    ['SUSPENDED' as const, '상점 정지'],
    ['CLOSED' as const, '폐점'],
  ])('%s는 「%s」을 돌려준다(states.md 상점)', (status, label) => {
    expect(storeStatusLabel(status)).toBe(label);
  });
});

describe('entities/store domain storeStatusTone', () => {
  it.each([
    ['ACTIVE' as const, 'ok'],
    ['SUSPENDED' as const, 'hot'],
    ['CLOSED' as const, 'mute'],
  ])('%s는 %s 톤이다', (status, tone) => {
    expect(storeStatusTone(status)).toBe(tone);
  });
});
