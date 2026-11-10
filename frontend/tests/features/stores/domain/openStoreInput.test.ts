import { describe, expect, it } from 'vitest';
import {
  PICKUP_ADDRESS_MAX_LENGTH,
  canSubmitOpenStore,
} from '@/features/stores/domain/openStoreInput';

describe('features/stores domain canSubmitOpenStore', () => {
  it.each([
    ['빈 문자열', '', false],
    ['공백만', '   ', false],
    ['500자', '서'.repeat(500), true],
    ['501자', '서'.repeat(501), false],
    ['공백만 500자', ' '.repeat(500), false],
  ])('%s는 %s를 돌려준다', (_label, input, expected) => {
    expect(canSubmitOpenStore(input)).toBe(expected);
  });

  it('서울은 true다', () => {
    expect(canSubmitOpenStore('서울')).toBe(true);
  });

  it(' 앞뒤 공백이 있는 서울도 true다', () => {
    expect(canSubmitOpenStore(' 서울 ')).toBe(true);
  });

  it('최대 길이 상수는 500이다', () => {
    expect(PICKUP_ADDRESS_MAX_LENGTH).toBe(500);
  });
});
