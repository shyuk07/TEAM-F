import { describe, expect, it } from 'vitest';
import { canSubmitClose } from '@/features/stores/domain/closeStoreInput';

const NAME = '망원베이커리';

describe('features/stores domain canSubmitClose (D-8: NFC 정규화 후 완전 일치)', () => {
  it('같은 이름이면 true다', () => {
    expect(canSubmitClose(NAME, NAME)).toBe(true);
  });

  it('앞뒤 공백을 포함하면 false다', () => {
    expect(canSubmitClose(` ${NAME} `, NAME)).toBe(false);
  });

  it('한 글자가 부족하면 false다', () => {
    expect(canSubmitClose('망원베이커', NAME)).toBe(false);
  });

  it('빈 입력은 false다', () => {
    expect(canSubmitClose('', NAME)).toBe(false);
  });

  it('대소문자만 다른 영문 상점명은 false다', () => {
    expect(canSubmitClose('mangwon bakery', 'Mangwon Bakery')).toBe(false);
  });

  it('NFC·NFD로 쓴 같은 글자는 true다', () => {
    const nfc = '빵집가게';
    const nfd = '빵집가게'.normalize('NFD');
    expect(nfd).not.toBe(nfc);
    expect(canSubmitClose(nfd, nfc)).toBe(true);
  });

  it('상점명이 빈 문자열이면 입력이 빈 문자열이어도 false다', () => {
    expect(canSubmitClose('', '')).toBe(false);
  });
});
